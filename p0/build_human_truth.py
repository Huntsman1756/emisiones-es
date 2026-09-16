"""P0-E.1: build truth-human-v1.json + gold-human-seal.json +
gold-human-audit.json from the sealed HUMAN gold store.

The human store lives under p0/results/gold_human/ and is written only
through GoldStore(adjudicator=<human id>) via p0.record_gold.
This builder never reads p0/results/gold/ (the provisional agent gold)
nor anything under p0/results/p0d/.
"""
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from p0.app import cases
from p0.app.gold import CRITICAL

REPO = Path(__file__).resolve().parent.parent
GOLD_DIR = REPO / 'p0' / 'results' / 'gold_human'
FIELDS = [f['id'] for f in
          json.load(open(REPO / 'p0' / 'manifests' / 'review-schema.json',
                         encoding='utf-8'))['fields']]


def sha256_file(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha256_json(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main(adjudication_mode, adjudicator_ids):
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
        'version': 'truth-human-v1',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'adjudication_mode': adjudication_mode,
        'adjudicator_ids': adjudicator_ids,
        'n_cases': len(cases_out),
        'n_fields_per_case': len(FIELDS),
        'cases': cases_out,
    }
    truth['truth_sha256'] = sha256_json(
        {k: v for k, v in truth.items() if k != 'truth_sha256'})
    (GOLD_DIR / 'truth-human-v1.json').write_text(
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
        'artifact': 'gold-human-seal',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'truth_sha256': truth['truth_sha256'],
        'sample_sha256': sha256_file(REPO / 'p0' / 'manifests' / 'sample.json'),
        'review_schema_sha256': sha256_file(
            REPO / 'p0' / 'manifests' / 'review-schema.json'),
        'protocol_sha256': sha256_file(
            REPO / 'p0' / 'manifests' / 'protocol.json'),
        'source_document_sha256': doc_shas,
        'adjudication_mode': adjudication_mode,
        'adjudicator_ids': adjudicator_ids,
        'status_totals': dict(status_tot),
    }
    seal['seal_sha256'] = sha256_json(seal)
    (GOLD_DIR / 'gold-human-seal.json').write_text(
        json.dumps(seal, indent=1, ensure_ascii=False), encoding='utf-8')

    audit = {
        'artifact': 'gold-human-audit',
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
        'p0_adm_123067': {
            'note': 'document prints two conflicting underlying ISINs; '
                    'resolution under official-source-only rules is '
                    'whatever the human adjudicator recorded — Bloomberg '
                    'was not used'},
    }
    (GOLD_DIR / 'gold-human-audit.json').write_text(
        json.dumps(audit, indent=1, ensure_ascii=False), encoding='utf-8')

    print('cases:', len(sealed), 'units:', sum(status_tot.values()))
    print('status:', dict(status_tot))
    print('issues:', len(issues))
    print('truth sha:', truth['truth_sha256'][:16])
    print('seal sha:', seal['seal_sha256'][:16])


if __name__ == '__main__':
    import sys
    # python -m p0.build_human_truth <MODE> <ADJ_ID[,ADJ_ID,...]>
    main(sys.argv[1], sys.argv[2].split(','))
