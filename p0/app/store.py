"""Review store: decisions, events, timing. JSONL, append-only."""
import json
import math
import os
import threading
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

from . import cases, evidence, models


class StoreError(Exception):
    pass


_locks = {}
_locks_guard = threading.Lock()


def _locked(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self.transaction():
            return method(self, *args, **kwargs)
    return call


def _timestamp(ts):
    ts = time.time() if ts is None else ts
    if type(ts) not in (int, float) or not math.isfinite(ts) or ts < 0:
        raise StoreError('timestamp must be finite and nonnegative')
    return ts


def _identity(reviewer_id, case_id):
    if not all(isinstance(x, str) and x.strip() and len(x) <= 200
               for x in (reviewer_id, case_id)):
        raise StoreError('reviewer_id and case_id must be nonempty strings')


class ReviewStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.decisions_path = self.root / 'decisions.jsonl'
        self.events_path = self.root / 'events.jsonl'
        self.reviews_path = self.root / 'reviews.jsonl'
        with _locks_guard:
            self._lock, self._local = _locks.setdefault(
                self.root, (threading.RLock(), threading.local()))

    @contextmanager
    def transaction(self):
        with self._lock:
            if getattr(self._local, 'active', False):
                yield
                return
            with (self.root / '.store.lock').open('a+b') as lock:
                if lock.tell() == 0:
                    lock.write(b'0')
                    lock.flush()
                lock.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                self._local.active = True
                try:
                    yield
                finally:
                    self._local.active = False
                    lock.seek(0)
                    if os.name == 'nt':
                        msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    @_locked
    def _append(self, path, obj):
        try:
            data = (json.dumps(obj, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
        except (ValueError, TypeError, UnicodeError) as exc:
            raise StoreError('record must be finite JSON') from exc
        self._read(path)
        with Path(path).open('ab') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

    @_locked
    def _read(self, path):
        path = Path(path)
        if not path.exists():
            return []
        try:
            data = path.read_bytes()
            if data and not data.endswith(b'\n'):
                raise ValueError('incomplete record')
            rows = [json.loads(line, parse_constant=self._invalid_constant)
                    for line in data.decode('utf-8').splitlines() if line.strip()]
            if any(not isinstance(row, dict) for row in rows):
                raise ValueError('record must be an object')
            return rows
        except (ValueError, UnicodeError) as exc:
            raise StoreError(f'corrupt log: {path.name}; recovery required') from exc

    @staticmethod
    def _invalid_constant(value):
        raise ValueError('nonfinite JSON')

    def _submitted(self, case_id, reviewer_id):
        return next((r for r in self._read(self.reviews_path)
                     if r['case_id'] == case_id and r['reviewer_id'] == reviewer_id), None)

    @_locked
    def record_event(self, reviewer_id, case_id, event_type, payload=None, ts=None):
        _identity(reviewer_id, case_id)
        if event_type not in models.EVENT_TYPES:
            raise StoreError(f'unknown event_type {event_type}')
        if payload is not None and not isinstance(payload, dict):
            raise StoreError('event payload must be an object')
        if self._submitted(case_id, reviewer_id):
            raise StoreError('review already submitted')
        ts = _timestamp(ts)
        events = self._events(case_id, reviewer_id)
        if events and ts < events[-1]['ts']:
            raise StoreError('event timestamp precedes previous event')
        ev = {'ts': ts, 'reviewer_id': reviewer_id, 'case_id': case_id,
              'event_type': event_type, 'payload': payload if payload is not None else {}}
        self._append(self.events_path, ev)
        return ev

    def _events(self, case_id, reviewer_id):
        return [e for e in self._read(self.events_path)
                if e['case_id'] == case_id and e['reviewer_id'] == reviewer_id]

    @_locked
    def active_seconds(self, case_id, reviewer_id, now=None):
        review = self._submitted(case_id, reviewer_id)
        if review:
            return review['active_seconds']
        now = _timestamp(now)
        opened, total = None, 0.0
        for ev in self._events(case_id, reviewer_id):
            if ev['event_type'] in ('CASE_OPENED', 'CASE_RESUMED') and opened is None:
                opened = ev['ts']
            elif ev['event_type'] in ('CASE_PAUSED', 'CASE_SUBMITTED') and opened is not None:
                total += max(0, ev['ts'] - opened)
                opened = None
        if opened is not None:
            total += max(0, now - opened)
        return total

    @_locked
    def record_decision(self, reviewer_id, case_id, field, decision,
                        value=None, candidate_id=None,
                        origin='MACHINE_CANDIDATE', evidence_pointers=None,
                        ts=None, case_candidates=None, case_documents=None):
        _identity(reviewer_id, case_id)
        if self._submitted(case_id, reviewer_id):
            raise StoreError('review already submitted')
        if not isinstance(field, str) or field not in models.SCHEMA_TO_EXTRACTOR:
            raise StoreError('unknown review field')
        if decision not in models.HUMAN_DECISIONS:
            raise StoreError(f'not a human decision: {decision}')
        if origin not in models.ORIGINS:
            raise StoreError(f'unknown origin {origin}')
        if evidence_pointers is not None and not isinstance(evidence_pointers, list):
            raise StoreError('evidence_pointers must be a list')
        pointers = list(evidence_pointers or [])
        if candidate_id is None and decision in ('MISSING', 'NOT_APPLICABLE'):
            origin = 'FIELD_STATUS'
        if origin == 'FIELD_STATUS':
            if decision not in ('MISSING', 'NOT_APPLICABLE') or candidate_id is not None or value is not None:
                raise StoreError('FIELD_STATUS requires a missing/n/a decision without value or candidate')
        elif origin == 'MACHINE_CANDIDATE':
            cand = self._find_candidate(case_candidates, candidate_id)
            if cand is None:
                raise StoreError(f'unknown candidate {candidate_id}')
            if cand.get('field') not in models.SCHEMA_TO_EXTRACTOR[field]:
                raise StoreError('candidate does not support this schema field')
            if not pointers and decision == 'CONFIRMED':
                pointers = list(cand.get('evidence') or [])
        elif candidate_id is not None:
            raise StoreError('MANUAL_DISCOVERY cannot reference a candidate')
        if decision == 'CONFIRMED':
            if value is None or value == [] or value == {} or isinstance(value, str) and not value.strip():
                raise StoreError('CONFIRMED requires a value')
            if not pointers:
                raise StoreError('CONFIRMED requires evidence pointer')
        if origin == 'MANUAL_DISCOVERY' and not pointers:
            raise StoreError('MANUAL_DISCOVERY requires evidence pointer')
        if pointers and case_documents is None:
            case = cases.all_cases().get(case_id)
            if case is None:
                raise StoreError('case documents required for evidence authorization')
            case_documents = cases.document_ids(case)
        for pointer in pointers:
            status, detail = evidence.validate_pointer(pointer, case_documents)
            if status != 'OK':
                raise StoreError(f'BROKEN_EVIDENCE: {detail}')
        dec = {
            'case_id': case_id, 'reviewer_id': reviewer_id,
            'field': field, 'decision': decision, 'value': value,
            'candidate_id': candidate_id, 'origin': origin,
            'evidence_pointers': pointers,
            'created_at': _timestamp(ts),
        }
        self._append(self.decisions_path, dec)
        return dec

    @staticmethod
    def _find_candidate(candidates, candidate_id):
        if not isinstance(candidate_id, str) or not isinstance(candidates, list):
            return None
        matches = [c for c in candidates if isinstance(c, dict) and
                   c.get('candidate_id') == candidate_id]
        return matches[0] if len(matches) == 1 else None

    @_locked
    def decisions_for(self, case_id, reviewer_id):
        return [d for d in self._read(self.decisions_path)
                if d['case_id'] == case_id and d['reviewer_id'] == reviewer_id]

    def _finish_submit(self, review):
        co = review.get('closeout')
        if co and not any(c['case_id'] == review['case_id'] and
                          c['reviewer_id'] == review['reviewer_id']
                          for c in self._read(self.root / 'closeouts.jsonl')):
            self._append(self.root / 'closeouts.jsonl', co)
        return review

    @_locked
    def submit_review(self, reviewer_id, case_id, schema, ts=None,
                      reviewer_notes=None, case_documents=None):
        _identity(reviewer_id, case_id)
        prior = self._submitted(case_id, reviewer_id)
        if prior:
            return self._finish_submit(prior)
        ts = _timestamp(ts)
        if reviewer_notes is not None and (not isinstance(reviewer_notes, list) or
                                          any(not isinstance(n, str) for n in reviewer_notes)):
            raise StoreError('reviewer_notes must be a list of strings')
        decs = self.decisions_for(case_id, reviewer_id)
        by_field = {}
        for d in decs:
            by_field.setdefault(d['field'], []).append(d)
        unresolved_critical = [f['id'] for f in schema['fields']
                               if f['critical'] and f['id'] not in by_field]
        events = self._events(case_id, reviewer_id)
        if events and ts < events[-1]['ts']:
            raise StoreError('submission timestamp precedes previous event')
        ptrs = [p for d in decs for p in d.get('evidence_pointers', [])]
        audit = evidence.audit_case(case_id, ptrs, case_documents) if ptrs else {'ok': 0, 'total': 0}
        if audit['ok'] != audit['total']:
            raise StoreError('BROKEN_EVIDENCE: stored evidence no longer valid')
        n_ev = lambda t: sum(1 for e in events if e['event_type'] == t)
        review = {
            'case_id': case_id, 'reviewer_id': reviewer_id,
            'submitted_at': ts,
            'active_seconds': self.active_seconds(case_id, reviewer_id, now=ts),
            'n_decisions': len(decs), 'fields_decided': sorted(by_field),
            'unresolved_critical': unresolved_critical, 'decisions': decs,
        }
        paused_at, invalid_timing = None, False
        for ev in events:
            if ev['event_type'] == 'CASE_PAUSED' and paused_at is None:
                paused_at = ev['ts']
            elif ev['event_type'] in ('CASE_OPENED', 'CASE_RESUMED', 'CASE_SUBMITTED') and paused_at is not None:
                invalid_timing |= ev['ts'] - paused_at > 300
                paused_at = None
        if paused_at is not None:
            invalid_timing |= ts - paused_at > 300
        review['timing_status'] = 'INVALID_TIMING' if invalid_timing else 'VALID'
        review['closeout'] = {
            'reviewer_id': reviewer_id, 'case_id': case_id, 'submitted': True,
            'active_seconds': review['active_seconds'],
            'pause_count': n_ev('CASE_PAUSED'), 'focus_lost_count': n_ev('FOCUS_LOST'),
            'decisions_count': len(decs), 'critical_fields_unresolved': unresolved_critical,
            'evidence_jumps': n_ev('EVIDENCE_JUMP'), 'broken_evidence': 0,
            'manual_fields_added': sum(1 for d in decs if d.get('origin') == 'MANUAL_DISCOVERY'),
            'ui_errors': [e['payload'] for e in events if e['event_type'] == 'UI_ERROR'],
            'reviewer_notes': list(reviewer_notes or []),
        }
        self._append(self.reviews_path, review)
        return self._finish_submit(review)

    def check_freeze(self, freeze_file):
        import hashlib
        with open(freeze_file, encoding='utf-8') as f:
            spec = json.load(f)
        mism = []
        for name, ent in spec.get('files', {}).items():
            p = cases.REPO / ent['path']
            if not p.exists():
                mism.append((name, 'missing'))
                continue
            actual = hashlib.sha256(p.read_bytes()).hexdigest()
            if actual != ent['sha256']:
                mism.append((name, 'sha mismatch'))
        return mism
