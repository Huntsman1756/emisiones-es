"""Review store: decisions, events, timing. JSONL, append-only.

Invariants enforced here:
- only human decisions exist; candidates are never mutated
- CONFIRMED requires value + at least one valid evidence pointer
- MANUAL_DISCOVERY requires explicit evidence pointers
- MACHINE_CANDIDATE requires an existing candidate_id
"""
import json
import time
from pathlib import Path

from . import evidence, models


class StoreError(Exception):
    pass


class ReviewStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.decisions_path = self.root / 'decisions.jsonl'
        self.events_path = self.root / 'events.jsonl'
        self.reviews_path = self.root / 'reviews.jsonl'
        # open intervals: (case_id, reviewer_id) -> opened_at
        self._open = {}

    # ---------- append helpers ----------
    def _append(self, path, obj):
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(obj, ensure_ascii=False) + '\n')

    def _read(self, path):
        if not path.exists():
            return []
        return [json.loads(l) for l in
                open(path, encoding='utf-8').read().splitlines() if l.strip()]

    # ---------- events ----------
    def record_event(self, reviewer_id, case_id, event_type, payload=None,
                     ts=None):
        if event_type not in models.EVENT_TYPES:
            raise StoreError(f'unknown event_type {event_type}')
        ts = ts if ts is not None else time.time()
        ev = {'ts': ts, 'reviewer_id': reviewer_id, 'case_id': case_id,
              'event_type': event_type, 'payload': payload or {}}
        self._append(self.events_path, ev)
        self._timing_event(ev)
        return ev

    # ---------- timing ----------
    def _timing_event(self, ev):
        key = (ev['case_id'], ev['reviewer_id'])
        if ev['event_type'] == 'CASE_OPENED':
            self._open[key] = ev['ts']
        elif ev['event_type'] == 'CASE_RESUMED':
            if key not in self._open:
                self._open[key] = ev['ts']
        elif ev['event_type'] in ('CASE_PAUSED', 'CASE_SUBMITTED'):
            opened = self._open.pop(key, None)
            if opened is not None:
                self._append(self.root / 'intervals.jsonl', {
                    'case_id': key[0], 'reviewer_id': key[1],
                    'start': opened, 'end': ev['ts'],
                    'kind': ev['event_type']})
        # FOCUS_LOST is logged only; never auto-pauses (protocol §14)

    def active_seconds(self, case_id, reviewer_id, now=None):
        total = 0.0
        for it in self._read(self.root / 'intervals.jsonl'):
            if it['case_id'] == case_id and it['reviewer_id'] == reviewer_id:
                total += it['end'] - it['start']
        opened = self._open.get((case_id, reviewer_id))
        if opened is not None:
            total += (now or time.time()) - opened
        return total

    # ---------- decisions ----------
    def record_decision(self, reviewer_id, case_id, field, decision,
                        value=None, candidate_id=None,
                        origin='MACHINE_CANDIDATE', evidence_pointers=None,
                        ts=None, case_candidates=None):
        if decision not in models.HUMAN_DECISIONS:
            raise StoreError(f'not a human decision: {decision}')
        if origin not in models.ORIGINS:
            raise StoreError(f'unknown origin {origin}')
        # field-level status (MISSING / NOT_APPLICABLE) has no candidate
        if candidate_id is None and decision in ('MISSING',
                                                 'NOT_APPLICABLE'):
            origin = 'FIELD_STATUS'
        pointers = list(evidence_pointers or [])

        if decision == 'CONFIRMED':
            if value in (None, '', []):
                raise StoreError('CONFIRMED requires a value')
            if origin == 'MANUAL_DISCOVERY' and not pointers:
                raise StoreError(
                    'MANUAL_DISCOVERY CONFIRMED requires evidence pointer')
            if origin == 'MACHINE_CANDIDATE':
                cand = self._find_candidate(case_candidates, candidate_id)
                if cand is None:
                    raise StoreError(f'unknown candidate {candidate_id}')
                if not pointers:
                    pointers = cand.get('evidence', [])
            for p in pointers:
                status, detail = evidence.validate_pointer(p)
                if status != 'OK':
                    raise StoreError(f'BROKEN_EVIDENCE: {detail}')

        if origin == 'MACHINE_CANDIDATE' and candidate_id is None:
            raise StoreError('MACHINE_CANDIDATE requires candidate_id')
        if decision in ('REJECTED', 'CONFLICT') and \
                candidate_id is None and not pointers:
            raise StoreError(
                f'{decision} requires a candidate_id or evidence')

        dec = {
            'case_id': case_id, 'reviewer_id': reviewer_id,
            'field': field, 'decision': decision, 'value': value,
            'candidate_id': candidate_id, 'origin': origin,
            'evidence_pointers': pointers,
            'created_at': ts if ts is not None else time.time(),
        }
        self._append(self.decisions_path, dec)
        return dec

    @staticmethod
    def _find_candidate(candidates, candidate_id):
        if candidate_id is None or candidates is None:
            return None
        for c in candidates:
            if c.get('candidate_id') == candidate_id:
                return c
        return None

    def decisions_for(self, case_id, reviewer_id):
        return [d for d in self._read(self.decisions_path)
                if d['case_id'] == case_id and d['reviewer_id'] == reviewer_id]

    # ---------- submit ----------
    def submit_review(self, reviewer_id, case_id, schema, ts=None,
                      reviewer_notes=None):
        """Seal the review + write session close-out. Never blocks
        valid states; unresolved criticals are warnings only."""
        decs = self.decisions_for(case_id, reviewer_id)
        by_field = {}
        for d in decs:
            by_field.setdefault(d['field'], []).append(d)

        unresolved_critical = [
            f['id'] for f in schema['fields']
            if f['critical'] and f['id'] not in by_field]

        events = [e for e in self._read(self.events_path)
                  if e['case_id'] == case_id
                  and e['reviewer_id'] == reviewer_id]
        n_ev = lambda t: sum(1 for e in events
                             if e['event_type'] == t)
        ptrs = [p for d in decs for p in d.get('evidence_pointers', [])]
        audit = evidence.audit_case(case_id, ptrs)

        review = {
            'case_id': case_id, 'reviewer_id': reviewer_id,
            'submitted_at': ts if ts is not None else time.time(),
            'active_seconds': self.active_seconds(case_id, reviewer_id),
            'n_decisions': len(decs),
            'fields_decided': sorted(by_field),
            'unresolved_critical': unresolved_critical,
            'decisions': decs,
        }
        self._append(self.reviews_path, review)

        closeout = {
            'reviewer_id': reviewer_id, 'case_id': case_id,
            'submitted': True,
            'active_seconds': review['active_seconds'],
            'pause_count': n_ev('CASE_PAUSED'),
            'focus_lost_count': n_ev('FOCUS_LOST'),
            'decisions_count': len(decs),
            'critical_fields_unresolved': unresolved_critical,
            'evidence_jumps': n_ev('EVIDENCE_JUMP'),
            'broken_evidence': int(audit['ok'] < audit['total']),
            'manual_fields_added': sum(
                1 for d in decs if d.get('origin') == 'MANUAL_DISCOVERY'),
            'ui_errors': [e['payload'] for e in events
                          if e['event_type'] == 'UI_ERROR'],
            'reviewer_notes': list(reviewer_notes or []),
        }
        self._append(self.root / 'closeouts.jsonl', closeout)
        review['closeout'] = closeout
        return review

    # ---------- freeze guard ----------
    def check_freeze(self, freeze_file):
        """Verify sealed artifact hashes in p0/ui-freeze.json."""
        import hashlib
        spec = json.load(open(freeze_file, encoding='utf-8'))
        mism = []
        for name, ent in spec.get('files', {}).items():
            p = Path(__file__).resolve().parents[2] / ent['path']
            if not p.exists():
                mism.append((name, 'missing'))
                continue
            actual = hashlib.sha256(p.read_bytes()).hexdigest()
            if actual != ent['sha256']:
                mism.append((name, 'sha mismatch'))
        return mism
