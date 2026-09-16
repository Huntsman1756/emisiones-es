"""Session builder: ordered (case, mode) lists per reviewer.

P0 sessions come from the frozen assignments manifest — the reviewer
cannot choose or change mode. Dev sessions are free-form for UI work.
"""
import json
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNTIME = REPO / 'p0' / 'runtime'


def _write_session(reviewer_id, items, tag):
    sid = f'{tag}_{uuid.uuid4().hex[:8]}'
    sess = {'session_id': sid, 'reviewer_id': reviewer_id,
            'items': items, 'current': 0}
    RUNTIME.mkdir(parents=True, exist_ok=True)
    path = RUNTIME / f'session_{sid}.json'
    json.dump(sess, open(path, 'w', encoding='utf-8'), indent=1)
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
    mode_by_case = {a['case_id']: a[reviewer_key]
                    for a in assignments['assignments']}
    order = assignments['case_order'][reviewer_key]
    warm = assignments['warmup_assignment'][reviewer_key]
    items = [{'case_id': c, 'mode': 'ASSISTED', 'status': 'PENDING',
              'warmup': True} for c in warm]
    items += [{'case_id': c, 'mode': mode_by_case[c], 'status': 'PENDING',
               'warmup': False} for c in order]
    return _write_session(reviewer_key, items, 'p0')


def load_session(path):
    return json.load(open(path, encoding='utf-8'))


def save_session(path, sess):
    json.dump(sess, open(path, 'w', encoding='utf-8'), indent=1)
