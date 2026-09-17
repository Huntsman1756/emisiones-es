"""Session builder: ordered (case, mode) lists per reviewer.

P0 sessions come from the frozen assignments manifest — the reviewer
cannot choose or change mode. Dev sessions are free-form for UI work.
"""
import json
import os
import re
import tempfile
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNTIME = REPO / 'p0' / 'runtime'


def _write_session(reviewer_id, items, tag):
    if not isinstance(tag, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', tag):
        raise ValueError('invalid session tag')
    sid = f'{tag}_{uuid.uuid4().hex}'
    sess = {'session_id': sid, 'reviewer_id': reviewer_id,
            'items': items, 'current': 0}
    RUNTIME.mkdir(parents=True, exist_ok=True)
    path = RUNTIME / f'session_{sid}.json'
    save_session(path, sess)
    return path


def dev_session(cases, n=6, seed=1):
    """Mixed-mode dev session over G1 development cases."""
    import random
    rng = random.Random(seed)
    keys = sorted(k for k, c in cases.items()
                  if c.get('case_class') == 'DEVELOPMENT')
    rng.shuffle(keys)
    items = []
    for i, k in enumerate(keys[:n]):
        items.append({'case_id': k,
                      'mode': 'ASSISTED' if i % 2 == 0 else 'MANUAL',
                      'status': 'PENDING'})
    return _write_session('DEV_REVIEWER', items, 'dev')


def p0_session(reviewer_key, sample, assignments):
    """Frozen P0 session for REVIEWER_A | REVIEWER_B."""
    if reviewer_key not in assignments['reviewers']:
        raise ValueError('unknown assigned reviewer')
    mode_by_case = {a['case_id']: a[reviewer_key]
                    for a in assignments['assignments']}
    order = assignments['case_order'][reviewer_key]
    warm = assignments['warmup_assignment'][reviewer_key]
    holdout = {c['case_id'] for c in sample['cases']}
    warmup = {c['case_id'] for c in sample['warmup_cases']}
    if (len(mode_by_case) != len(assignments['assignments']) or
            set(mode_by_case) != holdout or set(order) != holdout or
            len(order) != len(holdout) or not set(warm) <= warmup or
            len(warm) != len(set(warm)) or holdout & warmup):
        raise ValueError('assignments do not match frozen sample')
    items = [{'case_id': c, 'mode': 'ASSISTED', 'status': 'PENDING',
              'warmup': True} for c in warm]
    items += [{'case_id': c, 'mode': mode_by_case[c], 'status': 'PENDING',
               'warmup': False} for c in order]
    return _write_session(reviewer_key, items, 'p0')


def validate_session(sess):
    if not isinstance(sess, dict):
        raise ValueError('session must be an object')
    if not isinstance(sess.get('session_id'), str) or not re.fullmatch(
            r'[A-Za-z0-9_-]{1,100}', sess['session_id']):
        raise ValueError('invalid session id')
    if not isinstance(sess.get('reviewer_id'), str) or not sess['reviewer_id'].strip():
        raise ValueError('invalid reviewer id')
    items = sess.get('items')
    if not isinstance(items, list):
        raise ValueError('session items must be a list')
    seen = set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('case_id'), str):
            raise ValueError('invalid session item')
        cid = item['case_id']
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', cid) or cid in seen:
            raise ValueError('invalid or duplicate session case')
        seen.add(cid)
        if item.get('mode') not in ('MANUAL', 'ASSISTED') or item.get('status') not in ('PENDING', 'DONE'):
            raise ValueError('invalid session mode or status')
    current = sess.get('current', 0)
    if type(current) is not int or not 0 <= current <= len(items):
        raise ValueError('invalid current session index')
    return sess


def load_session(path):
    with open(path, encoding='utf-8') as f:
        return validate_session(json.load(f))


def save_session(path, sess):
    validate_session(sess)
    path = Path(path)
    data = json.dumps(sess, ensure_ascii=False, allow_nan=False, indent=1)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
