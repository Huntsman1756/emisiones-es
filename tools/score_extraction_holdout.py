#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""G0-D one-shot: scoring del extraction holdout.

Usa EXACTAMENTE la semantica de classify() de tools/deep_dev_metrics.py
(contrato congelado). No modifica nada; solo lee predicciones selladas y truth.

Salidas:
  g0/results/g0-d-extraction-score.json
  g0/results/g0-d-provenance-score.json
  g0/results/g0-d-novelty-score.json
  g0/results/g0-d-performance.json
"""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from deep_dev_metrics import classify, has_real_value  # frozen semantics

PRED = ROOT / 'g0/results/g0-d-extraction-predictions.json'
TRUTH = ROOT / 'g0/holdout-truth/extraction-holdout-truth.json'
NOVELTY = ROOT / 'g0/manifests/novelty-field-map.json'
OUTDIR = ROOT / 'g0/results'

# Hard-gate groupings (sec. 12 del protocolo G0-D)
GATE_GROUPS = {
    'coupon_rate_family': {'fields': ['coupon_type', 'coupon_rate'], 'threshold': 0.95},
    'day_count': {'fields': ['day_count'], 'threshold': 0.95},
    'maturity': {'fields': ['maturity'], 'threshold': 0.99},
    'call_put': {'fields': ['call_dates', 'put_dates'], 'threshold': 0.90},
    'reset_fixing': {'fields': ['reset_dates', 'fixing_rules'], 'threshold': 0.90},
    'observation': {'fields': ['observation_dates'], 'threshold': 0.90},
    'barrier_strike_redemption': {
        'fields': ['barrier', 'strike', 'redemption_formula'], 'threshold': 0.90},
}


def main():
    res = json.loads(PRED.read_text(encoding='utf-8'))
    truth = json.loads(TRUTH.read_text(encoding='utf-8'))['cases']
    novelty_map = json.loads(NOVELTY.read_text(encoding='utf-8'))['fields']
    doc_only = {f for f, v in novelty_map.items()
                if v.get('worst_case_novelty') == 'DOCUMENT_ONLY'}

    per_field, per_stratum, details = {}, {}, []
    prov_total = prov_ok = prov_bad = 0
    prov_bad_cases = []

    for doc in res['documents']:
        ck, stratum = doc['case_key'], doc.get('stratum')
        t = truth.get(ck, {}).get('truth', {})
        for f in doc['fields']:
            tv = t.get(f['field'])
            if tv is None:
                continue
            c = classify(tv, f)
            details.append({'case': ck, 'stratum': stratum, 'field': f['field'],
                            'truth': tv, 'status': f['status'], 'cls': c,
                            'value': f.get('value'),
                            'raw': f.get('raw_lexeme')})
            pf = per_field.setdefault(f['field'], {})
            pf[c] = pf.get(c, 0) + 1
            pf['n'] = pf.get('n', 0) + 1
            ps = per_stratum.setdefault(stratum, {})
            ps[c] = ps.get(c, 0) + 1
            ps['n'] = ps.get('n', 0) + 1
            # provenance: cualquier valor factual emitido (correcto o no)
            if has_real_value(f) or (f.get('value') is not None
                                     and str(f.get('value')) != 'NOT_APPLICABLE'):
                prov_total += 1
                ev = f.get('evidence') or []
                ok = (bool(ev) and f.get('extractor')
                      and all(e.get('source') and e.get('snapshot_sha256')
                              and e.get('page') is not None
                              and e.get('extractor')
                              and (e.get('excerpt') or f.get('raw_lexeme'))
                              for e in ev[:1]))
                if ok:
                    prov_ok += 1
                else:
                    prov_bad += 1
                    prov_bad_cases.append({'case': ck, 'field': f['field'],
                                           'value': f.get('value'),
                                           'n_evidence': f.get('n_evidence')})

    for fld, m in per_field.items():
        tp = m.get('TP', 0) + m.get('TP_RAW', 0)
        fp = m.get('FP', 0) + m.get('FP_RAW', 0) + m.get('SPURIOUS_NA', 0)
        fn = m.get('FN', 0) + m.get('FN_NA', 0)
        m['precision'] = round(tp / (tp + fp), 4) if tp + fp else None
        m['recall'] = round(tp / (tp + fn), 4) if tp + fn else None
        m['n_present'] = m.get('TP', 0) + m.get('TP_RAW', 0) + fn
        m['n_absent'] = m.get('TN', 0) + fp
        m['n_na'] = m.get('CORRECT_NA', 0)

    # gate per group
    gates = {}
    for gname, g in GATE_GROUPS.items():
        tp = fp = fn = 0
        for fld in g['fields']:
            m = per_field.get(fld, {})
            tp += m.get('TP', 0) + m.get('TP_RAW', 0)
            fp += (m.get('FP', 0) + m.get('FP_RAW', 0)
                   + m.get('SPURIOUS_NA', 0))
            fn += m.get('FN', 0) + m.get('FN_NA', 0)
        prec = tp / (tp + fp) if tp + fp else None
        rec = tp / (tp + fn) if tp + fn else None
        gates[gname] = {'tp': tp, 'fp': fp, 'fn': fn,
                        'precision': round(prec, 4) if prec is not None else None,
                        'recall': round(rec, 4) if rec is not None else None,
                        'threshold_precision': g['threshold'],
                        'gate': ('PASS' if prec is not None and prec >= g['threshold']
                                 else 'FAIL' if prec is not None else 'NO_EVALUABLE')}

    # novelty / OSS_DELTA
    novelty_docs = []
    n_delta = 0
    for doc in res['documents']:
        ck = doc['case_key']
        t = truth.get(ck, {}).get('truth', {})
        has_delta = False
        doc_only_terms = []
        for f in doc['fields']:
            tv = t.get(f['field'])
            if tv in ('PRESENT', 'MULTI') and f['field'] in doc_only:
                c = classify(tv, f)
                doc_only_terms.append({'field': f['field'], 'truth': tv,
                                       'cls': c})
                if c in ('TP', 'TP_RAW'):
                    has_delta = True
        if has_delta:
            n_delta += 1
        novelty_docs.append({'case_key': ck, 'stratum': doc.get('stratum'),
                             'has_material_document_only_delta': has_delta,
                             'document_only_terms': doc_only_terms})
    novelty_pct = n_delta / len(res['documents'])

    # performance
    runtimes = [d['runtime_s'] for d in res['documents'] if d.get('runtime_s')]
    runtimes.sort()
    perf = {'n_docs': len(res['documents']),
            'total_runtime_s': round(sum(runtimes), 1),
            'median_s': round(statistics.median(runtimes), 1),
            'p90_s': round(runtimes[int(len(runtimes) * 0.9) - 1], 1),
            'max_s': round(max(runtimes), 1),
            'per_doc': {d['case_key']: d['runtime_s'] for d in res['documents']}}

    totals = {}
    for d in details:
        totals[d['cls']] = totals.get(d['cls'], 0) + 1

    score = {'n_docs': len(res['documents']),
             'scoring_contract': 'deep_dev_metrics.classify (frozen)',
             'totals': totals,
             'per_field': per_field,
             'per_stratum': per_stratum,
             'hard_gates': gates,
             'details': details}
    (OUTDIR / 'g0-d-extraction-score.json').write_text(
        json.dumps(score, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8')
    (OUTDIR / 'g0-d-provenance-score.json').write_text(json.dumps({
        'accepted_factual_values': prov_total,
        'evidence_backed': prov_ok,
        'provenance_bad': prov_bad,
        'pct_backed': round(prov_ok / prov_total, 4) if prov_total else None,
        'gate_100pct': 'PASS' if prov_bad == 0 else 'FAIL',
        'bad_cases': prov_bad_cases}, indent=2, ensure_ascii=False),
        encoding='utf-8')
    (OUTDIR / 'g0-d-novelty-score.json').write_text(json.dumps({
        'n_docs': len(res['documents']),
        'n_with_document_only_delta': n_delta,
        'pct': round(novelty_pct, 4),
        'threshold': 0.80,
        'required_min': 24,
        'gate': 'PASS' if n_delta >= 24 else 'FAIL',
        'per_doc': novelty_docs}, indent=2, ensure_ascii=False), encoding='utf-8')
    (OUTDIR / 'g0-d-performance.json').write_text(
        json.dumps(perf, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"{'field':<26}{'TP':>3}{'RAW':>3}{'FP':>3}{'sNA':>3}{'FN':>4}"
          f"{'cNA':>4}{'TN':>3}{'prec':>7}{'rec':>7}")
    for fld in sorted(per_field):
        m = per_field[fld]
        print(f"{fld:<26}{m.get('TP',0):>3}{m.get('TP_RAW',0):>3}"
              f"{m.get('FP',0):>3}{m.get('SPURIOUS_NA',0):>3}"
              f"{m.get('FN',0)+m.get('FN_NA',0):>4}{m.get('CORRECT_NA',0):>4}"
              f"{m.get('TN',0):>3}{str(m['precision']):>7}{str(m['recall']):>7}")
    print('\nHARD GATES:')
    for g, v in gates.items():
        print(f"  {g:<28} prec={v['precision']} thr={v['threshold_precision']} "
              f"tp={v['tp']} fp={v['fp']} fn={v['fn']} -> {v['gate']}")
    print(f"\nPROVENANCE: {prov_ok}/{prov_total} backed "
          f"({'PASS' if prov_bad == 0 else 'FAIL'})")
    print(f"NOVELTY: {n_delta}/30 = {novelty_pct:.1%} "
          f"({'PASS' if n_delta >= 24 else 'FAIL'})")
    print(f"PERF: total={perf['total_runtime_s']}s median={perf['median_s']}s "
          f"p90={perf['p90_s']}s max={perf['max_s']}s")
    print(f"\nTOTALS: {totals}")


if __name__ == '__main__':
    main()
