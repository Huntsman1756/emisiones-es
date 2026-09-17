"""P0-E.1 joint assembly for JOINT_REVIEWER_A_B.

  python -m p0.joint_gold diff            # report A<->B discrepancies
  python -m p0.joint_gold agreements      # write agreeing units to joint store
  python -m p0.joint_gold audit-sample    # 20% random audit of agreements
  python -m p0.joint_gold seal            # seal joint cases once complete

Reads ONLY the two independent human stores under
p0/results/gold_human/{A,B}/ — never the provisional agent gold nor
P0-D outputs.
"""
import hashlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from p0.app.gold import GoldStore, ALL_FIELDS, CRITICAL

REPO = Path(__file__).resolve().parent.parent
HUMAN = REPO / 'p0' / 'results' / 'gold_human'
JOINT_ADJ = 'JOINT_REVIEWER_A_B'


def _latest(root):
    units = defaultdict(dict)
    p = Path(root) / 'gold.jsonl'
    for l in p.read_text(encoding='utf-8').splitlines():
        if l.strip():
            d = json.loads(l)
            units[d['case_id']][d['field']] = d
    return units


def _canon(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def _agree(ua, ub):
    return ua['gold_status'] == ub['gold_status'] and \
        _canon(ua.get('gold_value')) == _canon(ub.get('gold_value'))


def _load_both():
    a, b = _latest(HUMAN / 'A'), _latest(HUMAN / 'B')
    assert len(a) == len(b) == 30, \
        f'stores incomplete: A={len(a)} B={len(b)}'
    for cid in a:
        assert len(a[cid]) == len(b[cid]) == 28, cid
    return a, b


def diff():
    a, b = _load_both()
    dis = []
    for cid in a:
        for f in ALL_FIELDS:
            if not _agree(a[cid][f], b[cid][f]):
                dis.append({'case_id': cid, 'field': f,
                            'critical': f in CRITICAL,
                            'A': {'status': a[cid][f]['gold_status'],
                                  'value': a[cid][f].get('gold_value'),
                                  'note': a[cid][f].get('adjudication_note')},
                            'B': {'status': b[cid][f]['gold_status'],
                                  'value': b[cid][f].get('gold_value'),
                                  'note': b[cid][f].get('adjudication_note')}})
    out = REPO / '.work' / 'p0e1' / 'discrepancies.json'
    out.write_text(json.dumps(dis, indent=1, ensure_ascii=False),
                   encoding='utf-8')
    print(f'disagreements: {len(dis)} / 840 -> {out}')
    print('critical disagreements:',
          sum(1 for d in dis if d['critical']))


def agreements():
    a, b = _load_both()
    joint = GoldStore(HUMAN, JOINT_ADJ)
    n = 0
    for cid in a:
        for f in ALL_FIELDS:
            ua, ub = a[cid][f], b[cid][f]
            if not _agree(ua, ub):
                continue
            joint.record_unit(
                cid, f, ua['gold_status'], ua.get('gold_value'),
                ua['evidence_pointers'],
                (ua.get('adjudication_note') or '') +
                ' [A+B agree]', ua.get('second_check'),
                ts=ua['created_at'])
            n += 1
    print(f'agreeing units written to joint store: {n}')


def audit_sample():
    a, b = _load_both()
    agreed = [(cid, f) for cid in a for f in ALL_FIELDS
              if _agree(a[cid][f], b[cid][f])]
    # seed: first 8 hex of protocol sha256 -> deterministic, recorded
    psha = hashlib.sha256(
        (REPO / 'p0' / 'manifests' / 'protocol.json')
        .read_bytes()).hexdigest()
    seed = int(psha[:8], 16)
    rng = random.Random(seed)
    n = max(1, round(0.20 * len(agreed)))
    sample = sorted(rng.sample(agreed, n))
    out = REPO / '.work' / 'p0e1' / 'audit-20pct.json'
    out.write_text(json.dumps(
        {'seed': seed, 'seed_source': 'first 8 hex of protocol sha256',
         'protocol_sha256': psha, 'n': n, 'of': len(agreed),
         'units': [{'case_id': c, 'field': f} for c, f in sample]},
        indent=1, ensure_ascii=False), encoding='utf-8')
    print(f'20% audit sample: {n}/{len(agreed)} units -> {out} '
          f'(seed={seed})')


def seal():
    joint = GoldStore(HUMAN, JOINT_ADJ)
    units = _latest(HUMAN)
    done = []
    for cid in units:
        if len(units[cid]) == 28:
            joint.seal_case(cid)
            done.append(cid)
        else:
            print(f'{cid}: {len(units[cid])}/28 — NOT sealed')
    print(f'sealed {len(done)}/30')


if __name__ == '__main__':
    {'diff': diff, 'agreements': agreements,
     'audit-sample': audit_sample, 'seal': seal}[sys.argv[1]]()
