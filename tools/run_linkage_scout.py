"""Ejecuta el linker determinista sobre linkage-scout.json (56 casos).
NO lee el holdout. Escribe g0/results/linkage-scout-results.json."""
import json, sys
from pathlib import Path

sys.path.insert(0, 'src')
from emissions_es.linking.linker import adjudicate
from emissions_es.linking.rules import Candidate, KnowledgeBase, SourceRecord

obs = json.load(open('.work/observations.json', encoding='utf-8'))
kb = KnowledgeBase(folletos=obs['folletos'], ccff=obs['ccff'],
                   admisiones=obs['admisiones'])
by_key = {}
for o in obs['folletos'] + obs['ccff'] + obs['admisiones']:
    by_key[o['source_record_key']] = o

import os
MANIFEST = sys.argv[1] if len(sys.argv) > 1 else \
    'g0/manifests/linkage-scout.json'
OUT = sys.argv[2] if len(sys.argv) > 2 else \
    'g0/results/linkage-scout-results.json'
man = json.load(open(MANIFEST, encoding='utf-8'))

def mk_src(s):
    o = by_key.get(s['record_key'], {})
    return SourceRecord(
        family=s['family'], record_key=s['record_key'],
        registro_oficial=s.get('registro_oficial') or o.get('registro_oficial'),
        version_suffix=s.get('version_suffix') or o.get('version_suffix'),
        rol=s.get('rol') or o.get('rol'),
        isin=s.get('isin') or o.get('isin'),
        doc_url=s.get('doc_url') or o.get('doc_url'),
        numfol_link=s.get('numfol_link') or o.get('numfol_link'),
        emisor=s.get('emisor') or o.get('emisor'),
        fecha=s.get('fecha') or o.get('fecha'))

def mk_cand(c):
    return Candidate(type=c.get('type', 'unknown'),
                     registro_oficial=c.get('registro_oficial'),
                     isin=c.get('isin'), doc_url=c.get('doc_url'),
                     record_key=c.get('record_key'), rol=c.get('rol'),
                     version=c.get('version'))

results, tp, fp, fn, correct = [], 0, 0, 0, 0
for case in man['cases']:
    res = adjudicate(mk_src(case['source']), mk_cand(case['candidate']), kb)
    gold = case['label']
    ok = res.decision.value == gold
    correct += ok
    if res.decision.value == 'EXACT_LINK' and gold == 'EXACT_LINK': tp += 1
    elif res.decision.value == 'EXACT_LINK' and gold != 'EXACT_LINK': fp += 1
    elif res.decision.value != 'EXACT_LINK' and gold == 'EXACT_LINK': fn += 1
    results.append({'case_key': case['case_key'], 'stratum': case['stratum'],
                    'gold': gold, 'decision': res.decision.value,
                    'rule_id': res.rule_id, 'rule_version': res.rule_version,
                    'relation': res.relation,
                    'positive_evidence': res.positive_evidence,
                    'negative_evidence': res.negative_evidence,
                    'correct': ok})

from collections import Counter
by_stratum = Counter((r['stratum'], r['correct']) for r in results)
metrics = {
    'n': len(results),
    'accuracy': correct / len(results),
    'tp': tp, 'fp': fp, 'fn': fn,
    'precision': tp / (tp + fp) if tp + fp else None,
    'recall': tp / (tp + fn) if tp + fn else None,
    'ambiguous_predicted': sum(1 for r in results if r['decision'] == 'AMBIGUOUS'),
    'ambiguous_gold': sum(1 for c in man['cases'] if c['label'] == 'AMBIGUOUS'),
    'forced_ambiguous': 0,
}
metrics['forced_ambiguous'] = sum(
    1 for r in results
    if r['gold'] == 'AMBIGUOUS' and r['decision'] == 'EXACT_LINK')
out = {'manifest': os.path.basename(MANIFEST),
       'manifest_sha256': man.get('manifest_sha256'),
       'note': 'DEV METRICS != G0 VERDICT; thresholds de holdout intactos',
       'metrics': metrics,
       'per_stratum': {f'{s}|{"ok" if ok else "fail"}': n
                       for (s, ok), n in sorted(by_stratum.items())},
       'cases': results}
json.dump(out, open(OUT, 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(json.dumps(metrics, indent=1))
for r in results:
    if not r['correct']:
        print('FAIL', r['case_key'], r['stratum'], 'gold=', r['gold'],
              'got=', r['decision'], r['rule_id'], r['negative_evidence'])
