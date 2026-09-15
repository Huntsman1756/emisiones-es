"""G1-C: scoring de extraccion contra truth-v1 sellada.

Implementa scoring-contract.json:
 - labels PRESENT/MULTI/NA/ABSENT
 - multi-value element scoring (EXACT/PARTIAL/SUPERSET_WITH_ERROR/DISJOINT/MISSING)
 - TP/FP/FN por campo + exact 95% CI binomial
 - evidence tiers (<5 INSUFFICIENT, 5-14 DESCRIPTIVE, >=15 GATE_ELIGIBLE)
 - hard gates de precision (solo si gate_eligible)
 - safety: provenance 100%, invented 0, unverified 0
 - slice COLD_ISSUER vs SEEN
"""
import json
import re
import sys
from collections import Counter, defaultdict

PRED = 'g1/results/extraction-predictions.json'
TRUTH = sys.argv[1] if len(sys.argv) > 1 else \
    'g1/results/extraction-truth-v1.json'
OUT_PATH = sys.argv[2] if len(sys.argv) > 2 else \
    'g1/results/extraction-score.json'
EH = 'g1/manifests/g1-a1/extraction-holdout.json'

HARD_GATES_P = {'coupon_rate': 0.95, 'day_count': 0.95, 'maturity': 0.99,
                'call_put': 0.90, 'reset_fixing': 0.90, 'observation': 0.90,
                'barrier_strike_redemption': 0.90}
FAMILY = {
 'coupon_rate': ['coupon_rate'],
 'day_count': ['day_count'],
 'maturity': ['maturity'],
 'call_put': ['call_dates', 'put_dates'],
 'reset_fixing': ['reset_dates', 'fixing_rules'],
 'observation': ['observation_dates'],
 'barrier_strike_redemption': ['barrier', 'autocall', 'strike',
                               'redemption_formula'],
}

FIELDS = ['isin', 'currency', 'issue_date', 'maturity', 'denomination',
          'issued_amount', 'coupon_type', 'coupon_rate', 'benchmark', 'spread',
          'payment_frequency', 'day_count', 'call_dates',
          'business_day_convention', 'put_dates', 'reset_dates', 'fixing_rules',
          'ranking', 'subordination', 'redemption_formula', 'underlying',
          'barrier', 'autocall', 'observation_dates', 'settlement_type',
          'participation', 'cap', 'strike']


def norm(v):
    # DEFECT-EVAL-1 (documented deviation, see g1/reports/G1-C-FINAL-EVALUATION.md):
    # money observations serialize value as {'amount','currency','raw_number'};
    # stringifying the dict produced a repr that could never match a canonical
    # gold value. The frozen contract requires comparing "mismo valor
    # normalizado" — for a money dict that is the canonical amount in digits.
    # Also: numeric equivalence canonicalization ('2.50' == '2.5', '4.10' ==
    # '4.1', '100.00' == '100'); lexeme-vs-canonical matching stays string-wise.
    if v is None:
        return ''
    if isinstance(v, dict):
        if 'amount' in v:
            return re.sub(r'\D', '', str(v.get('amount') or ''))
        return str(v)
    if isinstance(v, list):
        return ' '.join(sorted(norm(x) for x in v))
    s = str(v).strip().lower()
    s = re.sub(r'\s+', ' ', s)
    s = s.replace(',', '.')
    if re.fullmatch(r'-?\d+(\.\d+)?', s):
        f = float(s)
        return str(int(f)) if f == int(f) else repr(f)
    return s


def pred_elements(obs):
    """Elementos de la prediccion aceptada: lista de valores (multi) o
    valor unico; raw_lexeme como elemento si no hay value."""
    if obs is None:
        return []
    if obs.get('status') not in ('OBSERVED', 'DERIVED'):
        return []
    if obs.get('confidence_class') in ('VALUE_UNVERIFIED', 'cross_reference'):
        return []
    v = obs.get('value')
    if v == 'NOT_APPLICABLE':
        return []
    if isinstance(v, list):
        return [norm(x) for x in v if norm(x)]
    nv = norm(v)
    if nv:
        return [nv]
    rl = norm(obs.get('raw_lexeme'))
    return [rl] if rl else []


def gold_elements(t):
    vals = t.get('values') or []
    return [norm(v) for v in vals if norm(v)]


def match(pred_set, gold_set):
    """Element scoring. Devuelve (TP,FP,FN,clase)."""
    ps, gs = set(pred_set), set(gold_set)
    tp = len(ps & gs)
    fp = len(ps - gs)
    fn = len(gs - ps)
    if not ps and not gs:
        return 0, 0, 0, 'NOT_APPLICABLE'
    if not ps:
        return tp, fp, fn, 'MISSING'
    if not gs:
        return tp, fp, 0, 'DISJOINT' if ps else 'NOT_APPLICABLE'
    if ps == gs:
        return tp, fp, fn, 'EXACT'
    if ps < gs:
        return tp, fp, fn, 'PARTIAL'
    if tp and fp:
        return tp, fp, fn, 'SUPERSET_WITH_ERROR'
    if not tp:
        return tp, fp, fn, 'DISJOINT'
    return tp, fp, fn, 'PARTIAL' if fn else 'EXACT'


def accepted_pred(er):
    """La observacion cuenta como emitida (para FP/TN con gold ABSENT)."""
    return bool(pred_elements((er or {}).get('observation')))


def ci95(k, n):
    if n == 0:
        return [None, None]
    from scipy.stats import beta
    return [round(float(beta.ppf(0.025, k, n - k + 1)), 4),
            round(float(beta.ppf(0.975, k + 1, n - k)), 4)]


def tier(pos):
    return 'INSUFFICIENT_EVIDENCE' if pos < 5 else \
           'DESCRIPTIVE_ONLY' if pos < 15 else 'GATE_ELIGIBLE'


def main():
    preds = {d['doc']: d for d in
             json.load(open(PRED, encoding='utf-8'))['documents']}
    truth = json.load(open(TRUTH, encoding='utf-8'))['cases']
    man = json.load(open(EH, encoding='utf-8'))
    cold = set(man['cold_issuer_slice']['docs']
               if isinstance(man['cold_issuer_slice'], dict)
               and 'docs' in man['cold_issuer_slice'] else [])
    if not cold:
        # cold slice = docs cuyo issuer esta en la lista de emisores frios
        uni = {r['source_record_key']: r for r in
               json.load(open('g1/manifests/universe.json',
                              encoding='utf-8'))['records']}
        cis = set(man['cold_issuer_slice']['issuers'])
        cold = {d['source_record_key'] for d in man['docs']
                if (uni.get(d['source_record_key'], {}).get('issuer_key')
                    or uni.get(d['source_record_key'], {}).get('issuer'))
                in cis}

    per_field = defaultdict(Counter)
    per_field_cold = defaultdict(Counter)
    per_field_seen = defaultdict(Counter)
    classes = Counter()
    failures = Counter()
    prov_bad, unverified, invented = [], [], []
    doc_rows = []
    n_obs_total = 0

    for ck, t in truth.items():
        p = preds.get(ck)
        if p is None:
            doc_rows.append({'doc': ck, 'note': 'no prediction'})
            continue
        tfields = t['fields']
        row = {'doc': ck, 'cold': ck in cold,
               'role_pred': p['classification']['document_role'],
               'scope_pred': p['classification']['scope_role'],
               'fields': {}}
        if p['classification']['scope_role'] == 'LIFECYCLE':
            row['note'] = 'lifecycle-scope: no term scoring'
            doc_rows.append(row)
            continue
        for field in FIELDS:
            spec = tfields.get(field, 'ABSENT')
            if isinstance(spec, dict):
                want = spec.get('label', 'ABSENT')
                gvals = spec.get('values') or []
            else:
                want = spec
                gvals = []
            er = p['fields'].get(field)
            obs = (er or {}).get('observation')
            if obs and obs.get('status') in ('OBSERVED', 'DERIVED'):
                n_obs_total += 1
                if obs.get('confidence_class') == 'VALUE_UNVERIFIED':
                    unverified.append(f'{ck}:{field}')
                if not obs.get('evidence'):
                    prov_bad.append(f'{ck}:{field}')
            pf = per_field[field]
            pcf = per_field_cold[field] if ck in cold else \
                per_field_seen[field]
            if want in ('NA', 'NOT_APPLICABLE'):
                continue
            pe = pred_elements(obs)
            if want in ('PRESENT', 'MULTI'):
                ge = gold_elements({'values': gvals}) if gvals else ['__present__']
                if not gvals:
                    # gold presence-level: match por presencia
                    tp, fp, fn = (1, 0, 0) if pe else (0, 0, 1)
                    cls = 'EXACT' if pe else 'MISSING'
                else:
                    tp, fp, fn, cls = match(pe, ge)
                pf['pos_gold'] += 1
                pcf['pos_gold'] += 1
                pf['TP'] += tp; pf['FP'] += fp; pf['FN'] += fn
                pcf['TP'] += tp; pcf['FP'] += fp; pcf['FN'] += fn
                classes[f'{field}:{cls}'] += 1
                row['fields'][field] = cls
                if er and er.get('failure') and cls == 'MISSING':
                    failures[f'{field}:{er["failure"]}'] += 1
            elif want == 'ABSENT':
                if pe:
                    pf['FP'] += len(pe)
                    pcf['FP'] += len(pe)
                    invented.append(f'{ck}:{field}')
                    row['fields'][field] = 'FP'
                else:
                    pf['TN'] += 1
                    pcf['TN'] += 1
        doc_rows.append(row)

    def summarize(pf):
        out = {}
        for f in FIELDS:
            ct = pf[f]
            pos = ct['pos_gold']
            tp, fp, fn = ct['TP'], ct['FP'], ct['FN']
            prec = tp / max(1, tp + fp)
            rec = tp / max(1, tp + fn)
            out[f] = {'positive_gold': pos, 'TP': tp, 'FP': fp, 'FN': fn,
                      'precision': round(prec, 4), 'recall': round(rec, 4),
                      'ci95_precision': ci95(tp, tp + fp),
                      'ci95_recall': ci95(tp, tp + fn),
                      'gate_eligible': tier(pos)}
        return out

    field_summary = summarize(per_field)
    gates = {}
    for fam, thr in HARD_GATES_P.items():
        c = Counter()
        for f in FAMILY[fam]:
            c += per_field[f]
        pos = sum(per_field[f]['pos_gold'] for f in FAMILY[fam])
        tp, fp = c['TP'], c['FP']
        prec = tp / max(1, tp + fp)
        gates[fam] = {'threshold': thr, 'positive_gold': pos,
                      'tier': tier(pos),
                      'precision': round(prec, 4),
                      'applies': tier(pos) == 'GATE_ELIGIBLE',
                      'pass': (prec >= thr) if tier(pos) == 'GATE_ELIGIBLE'
                      else 'NOT_GATE_ELIGIBLE'}

    role_acc = {}
    uni = {r['source_record_key']: r for r in
           json.load(open('g1/manifests/universe.json',
                          encoding='utf-8'))['records']}
    n_ok = n_meta = n_meta_ok = n_cont = n_cont_ok = n_unk = n_fc = 0
    for ck in truth:
        p = preds.get(ck)
        if not p or 'classification' not in p:
            continue
        exp = uni.get(ck, {}).get('document_role')
        got = p['classification']['document_role']
        sigs = ' '.join(p['classification'].get('signals') or [])
        meta_det = 'surface:' in sigs or 'meta:' in sigs
        if meta_det:
            n_meta += 1
            n_meta_ok += got == exp
        else:
            n_cont += 1
            n_cont_ok += got == exp
        n_ok += got == exp
        n_unk += got == 'UNKNOWN'
        n_fc += (got != exp and got != 'UNKNOWN')
        n_docs_cls = n_ok and True
    n_cls = sum(1 for ck in truth if preds.get(ck))
    role_acc = {'n': n_cls,
                'role_accuracy': round(n_ok / max(1, n_cls), 4),
                'metadata_determined': {'n': n_meta,
                                        'accuracy': round(n_meta_ok /
                                                          max(1, n_meta), 4)},
                'content_determined': {'n': n_cont,
                                       'accuracy': round(n_cont_ok /
                                                         max(1, n_cont), 4)},
                'unknown_rate': round(n_unk / max(1, n_cls), 4),
                'false_confident': n_fc}

    out = {
        'phase': 'G1-C extraction score', 'truth': TRUTH,
        'n_docs': len(truth),
        'per_field': field_summary,
        'hard_gates': gates,
        'safety': {
            'accepted_observations': n_obs_total,
            'provenance_violations': prov_bad,
            'provenance_rate': round(
                (n_obs_total - len(prov_bad)) / max(1, n_obs_total), 4),
            'value_unverified': unverified,
            'invented': invented},
        'multi_value_classes': dict(classes),
        'failure_taxonomy': dict(failures.most_common()),
        'cold_issuer': {'n_docs': len(cold),
                        'per_field': summarize(per_field_cold)},
        'seen_issuer': {'per_field': summarize(per_field_seen)},
        'classification': role_acc,
        'documents': doc_rows}
    json.dump(out, open(OUT_PATH, 'w',
                        encoding='utf-8'), ensure_ascii=False, indent=1)
    print('scored', len(truth), 'docs')
    print(json.dumps(gates, indent=1))
    print('prov', out['safety']['provenance_rate'],
          'inv', len(invented), 'unver', len(unverified))


if __name__ == '__main__':
    main()
