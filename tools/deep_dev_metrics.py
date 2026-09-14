#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Metricas por campo sobre extraction-deep-dev (DEVELOPMENT ONLY).

Clasificacion por par (doc, field):
  truth PRESENT/MULTI:
    status DERIVED/OBSERVED con valor / CONFLICT con algun valor real -> TP
    status OBSERVED con value=None (raw only)                          -> TP_RAW
    status MISSING                                                     -> FN
    status OBSERVED NOT_APPLICABLE                                     -> FN_NA
  truth NA:
    status OBSERVED NOT_APPLICABLE -> CORRECT_NA
    status MISSING                 -> FN
    valor real extraido            -> FP
  truth ABSENT:
    status MISSING -> TN
    OBSERVED NOT_APPLICABLE        -> SPURIOUS_NA
    valor real / raw               -> FP / FP_RAW
  truth no etiquetado -> UNLABELED (no entra en metricas)

Salida: g0/results/extraction-deep-dev-metrics.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / 'g0/results/extraction-deep-dev-results.json'
TRUTH = ROOT / 'g0/manifests/extraction-deep-dev-truth.json'
OUT = ROOT / 'g0/results/extraction-deep-dev-metrics.json'


def has_real_value(f):
    v = f.get('value')
    if v is None:
        return False
    if isinstance(v, list):
        return any(x is not None and str(x) != 'NOT_APPLICABLE' for x in v)
    return str(v) != 'NOT_APPLICABLE'


def is_na_obs(f):
    v = f.get('value')
    if isinstance(v, list):
        return all(x is None or str(x) == 'NOT_APPLICABLE' for x in v)
    return v is not None and str(v) == 'NOT_APPLICABLE'


def classify(truth, f):
    st = f['status']
    if truth in ('PRESENT', 'MULTI'):
        if st == 'MISSING':
            return 'FN'
        if is_na_obs(f):
            return 'FN_NA'
        if st == 'CONFLICT':
            return 'TP' if has_real_value(f) else 'FN'
        if f.get('value') is None:
            return 'TP_RAW'
        return 'TP'
    if truth == 'NA':
        if st == 'MISSING':
            return 'FN'
        if is_na_obs(f):
            return 'CORRECT_NA'
        return 'FP' if has_real_value(f) else 'FP_RAW'
    if truth == 'ABSENT':
        if st == 'MISSING':
            return 'TN'
        if is_na_obs(f):
            return 'SPURIOUS_NA'
        return 'FP' if has_real_value(f) else 'FP_RAW'
    return 'UNLABELED'


def main():
    res = json.loads(RES.read_text(encoding='utf-8'))
    truth = json.loads(TRUTH.read_text(encoding='utf-8'))['cases']
    per_field = {}
    details = []
    for doc in res['documents']:
        ck = doc['case_key']
        t = truth.get(ck, {}).get('truth', {})
        for f in doc['fields']:
            tv = t.get(f['field'])
            if tv is None:
                continue
            c = classify(tv, f)
            details.append({'case': ck, 'field': f['field'], 'truth': tv,
                            'status': f['status'], 'cls': c,
                            'value': f.get('value')})
            pf = per_field.setdefault(f['field'], {})
            pf[c] = pf.get(c, 0) + 1
            pf['n'] = pf.get('n', 0) + 1
    for fld, m in per_field.items():
        tp = m.get('TP', 0) + m.get('TP_RAW', 0)
        fp = m.get('FP', 0) + m.get('FP_RAW', 0) + m.get('SPURIOUS_NA', 0)
        fn = m.get('FN', 0) + m.get('FN_NA', 0)
        m['precision'] = round(tp / (tp + fp), 3) if tp + fp else None
        m['recall'] = round(tp / (tp + fn), 3) if tp + fn else None
    out = {'per_field': per_field, 'details': details}
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str),
                   encoding='utf-8')
    print(f"{'field':<26} {'TP':>3} {'RAW':>3} {'FP':>3} {'sNA':>3} {'FN':>4} "
          f"{'cNA':>4} {'TN':>3} {'prec':>6} {'rec':>6}")
    for fld in sorted(per_field):
        m = per_field[fld]
        print(f"{fld:<26} {m.get('TP',0):>3} {m.get('TP_RAW',0):>3} "
              f"{m.get('FP',0):>3} {m.get('SPURIOUS_NA',0):>3} "
              f"{m.get('FN',0)+m.get('FN_NA',0):>4} {m.get('CORRECT_NA',0):>4} "
              f"{m.get('TN',0):>3} "
              f"{str(m['precision']):>6} {str(m['recall']):>6}")


if __name__ == '__main__':
    main()
