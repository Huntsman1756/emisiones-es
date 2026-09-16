"""P0-E: build truth-v1.json + gold-seal.json + gold-audit.json from the
sealed per-case gold units in p0/results/gold/gold.jsonl.

No P0-D review data is read here — gold derives only from adjudicated units.
"""
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from p0.app import cases
from p0.app.gold import CRITICAL

REPO = Path(__file__).resolve().parent.parent
GOLD_DIR = REPO / 'p0' / 'results' / 'gold'
FIELDS = [f['id'] for f in
          json.load(open(REPO / 'p0' / 'manifests' / 'review-schema.json',
                         encoding='utf-8'))['fields']]


def sha256_file(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha256_json(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main():
    sealed = [json.loads(l) for l in
              open(GOLD_DIR / 'gold_cases.jsonl', encoding='utf-8')]
    units = defaultdict(dict)
    for l in open(GOLD_DIR / 'gold.jsonl', encoding='utf-8'):
        d = json.loads(l)
        units[d['case_id']][d['field']] = d  # latest wins

    cases_out = {}
    issues = []
    for s in sealed:
        cid = s['case_id']
        u = units[cid]
        missing = [f for f in FIELDS if f not in u]
        if missing:
            issues.append({'case_id': cid, 'issue': 'missing_fields',
                           'fields': missing})
        for f in FIELDS:
            if f not in u:
                continue
            unit = u[f]
            if unit['gold_status'] == 'CONFIRMED_VALUE' and \
                    not unit['evidence_pointers']:
                issues.append({'case_id': cid, 'field': f,
                               'issue': 'confirmed_without_evidence'})
            if f in CRITICAL and not unit.get('critical_verified'):
                issues.append({'case_id': cid, 'field': f,
                               'issue': 'critical_not_verified'})
        cases_out[cid] = {
            'case_id': cid,
            'sealed_at': s.get('sealed_at'),
            'fields': {f: {
                'gold_status': u[f]['gold_status'],
                'gold_value': u[f].get('gold_value'),
                'evidence_pointers': u[f].get('evidence_pointers', []),
                'adjudication_note': u[f].get('adjudication_note'),
                'critical_verified': u[f].get('critical_verified', False),
                'second_check': u[f].get('second_check'),
            } for f in FIELDS if f in u},
        }

    truth = {
        'version': 'truth-v1',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'adjudicator': 'ADJUDICATOR_C',
        'adjudicator_type': 'AGENT',
        'gold_independence': 'INDEPENDENT_THIRD_REVIEWER_AGENT',
        'n_cases': len(cases_out),
        'n_fields_per_case': len(FIELDS),
        'cases': cases_out,
    }
    truth_sha = sha256_json(truth)
    truth['truth_sha256'] = truth_sha
    (GOLD_DIR / 'truth-v1.json').write_text(
        json.dumps(truth, indent=1, ensure_ascii=False), encoding='utf-8')

    status_tot = Counter(
        cases_out[c]['fields'][f]['gold_status']
        for c in cases_out for f in cases_out[c]['fields'])

    doc_shas = {}
    for c in json.load(open(REPO / 'p0' / 'manifests' / 'sample.json',
                            encoding='utf-8'))['cases']:
        key = c['source_record_key']
        p = cases.pdf_path(key)
        if p:
            doc_shas[key] = sha256_file(p)

    seal = {
        'artifact': 'gold-seal',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'truth_sha256': sha256_json(
            json.loads((GOLD_DIR / 'truth-v1.json')
                       .read_text(encoding='utf-8'))),
        'sample_sha256': sha256_file(REPO / 'p0' / 'manifests' / 'sample.json'),
        'review_schema_sha256': sha256_file(
            REPO / 'p0' / 'manifests' / 'review-schema.json'),
        'protocol_sha256': sha256_file(
            REPO / 'p0' / 'manifests' / 'protocol.json'),
        'source_document_sha256': doc_shas,
        'adjudicator': 'ADJUDICATOR_C',
        'adjudicator_type': 'AGENT',
        'gold_independence': 'INDEPENDENT_THIRD_REVIEWER_AGENT',
        'status_totals': dict(status_tot),
    }
    seal['seal_sha256'] = sha256_json(seal)
    (GOLD_DIR / 'gold-seal.json').write_text(
        json.dumps(seal, indent=1, ensure_ascii=False), encoding='utf-8')

    audit = {
        'artifact': 'gold-audit',
        'created_at': seal['created_at'],
        'cases_sealed': len(sealed),
        'fields_per_case': len(FIELDS),
        'total_units': sum(status_tot.values()),
        'status_totals': dict(status_tot),
        'critical_fields': sorted(CRITICAL),
        'critical_verified_count': sum(
            1 for c in cases_out.values() for f in c['fields']
            if f in CRITICAL and c['fields'][f]['critical_verified']),
        'consistency_issues': issues,
        'p0d_inc_1': {
            'case_id': 'P0-ADM_123092',
            'note': 'storage incident during P0-D review persistence; '
                    'gold adjudicated normally from source documents — '
                    'incident is workflow/product scope, not truth scope'},
    }
    (GOLD_DIR / 'gold-audit.json').write_text(
        json.dumps(audit, indent=1, ensure_ascii=False), encoding='utf-8')

    print('cases:', len(sealed), 'units:', sum(status_tot.values()))
    print('status:', dict(status_tot))
    print('issues:', len(issues))
    print('truth sha:', truth_sha[:16])
    print('seal sha:', seal['seal_sha256'][:16])


if __name__ == '__main__':
    main()
