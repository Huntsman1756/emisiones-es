"""G1-C EVALUATION A — linkage holdout predictions (n=124).

Traduce los casos del holdout a SourceRecord/Candidate del linker congelado,
ejecuta link() y sella predicciones. Harness de evaluacion; cero cambios de
linker. Gold (labels) ya existe en el manifest — NO se lee para predecir.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, 'src')
from emissions_es.linking.rules import Candidate, KnowledgeBase, SourceRecord
from emissions_es.linking.family_linker import link

LK = 'g1/manifests/g1-a1/linkage-holdout.json'
OUT = Path('g1/results/linkage-predictions.json')

uni = json.load(open('g1/manifests/universe.json', encoding='utf-8'))['records']
obs = json.load(open('.work/observations.json', encoding='utf-8'))
by_key = {r['source_record_key']: r for r in uni}


def _split_reg(reg):
    if not reg:
        return None, None
    if '.' in reg:
        b, s = reg.split('.', 1)
        return b, '.' + s
    if '-' in reg and reg.rsplit('-', 1)[-1].isdigit():
        b, s = reg.rsplit('-', 1)
        return b, '-' + s
    return reg, None


def urec_to_obs(r):
    fam = {'CNMV_CCFF': 'cnmv_ccff',
           'CNMV_FOLLETOS_EMISION': 'cnmv_folletos_emision',
           'CNMV_FOLLETO_DETAIL': 'cnmv_folletos_emision',
           'CNMV_ADMISSION': 'cnmv_admision'}[r['acquisition_surface']]
    base, vs = _split_reg(r.get('registro_oficial'))
    return {'family': fam, 'source_record_key': r['source_record_key'],
            'registro_oficial': base, 'version_suffix': vs,
            'rol': r.get('denominacion') or r.get('document_role'),
            'emisor': r.get('issuer'), 'isin': r.get('isin'),
            'doc_url': r.get('document_url'),
            'numfol_link': (r.get('numfol')
                            if r['acquisition_surface'] == 'CNMV_CCFF'
                            else None),
            'fecha': r.get('fecha_registro')}


folletos = [urec_to_obs(r) for r in uni
            if r['acquisition_surface'] in ('CNMV_FOLLETOS_EMISION',
                                            'CNMV_FOLLETO_DETAIL')]
ccff = [urec_to_obs(r) for r in uni if r['acquisition_surface'] == 'CNMV_CCFF']
adm = [urec_to_obs(r) for r in uni if r['acquisition_surface'] == 'CNMV_ADMISSION']
kb = KnowledgeBase(folletos=folletos + obs['folletos'],
                   ccff=ccff + obs['ccff'],
                   admisiones=adm + obs['admisiones'])


def src_for(key):
    r = by_key.get(key)
    if r is not None:
        o = urec_to_obs(r)
        return SourceRecord(
            family=o['family'], record_key=key,
            registro_oficial=o['registro_oficial'],
            version_suffix=o['version_suffix'], rol=o['rol'],
            isin=o['isin'], doc_url=o['doc_url'],
            numfol_link=o['numfol_link'], emisor=o['emisor'],
            fecha=o['fecha'])
    # claves sinteticas de programa/familia -> registro base equivalente
    num = key.split('_', 1)[1]
    base_key = f'FOL_{num}'
    r = by_key.get(base_key)
    emisor = r.get('issuer') if r else None
    rol = (r.get('denominacion') or r.get('document_role')) if r else None
    return SourceRecord(family='cnmv_folletos_emision', record_key=key,
                        registro_oficial=num, rol=rol, emisor=emisor)


CAND_TYPE = {'base_prospectus': 'folleto',
             'any_base_prospectus': 'folleto',
             'family': 'folleto',
             'final_terms': 'ccff_doc',
             'final_terms_any': 'ccff_doc'}


def cand_for(c):
    t = CAND_TYPE.get(c.get('type'), 'unknown')
    reg = c.get('numfol')
    rk = c.get('record_key')
    if rk and rk in by_key:
        reg = (by_key[rk].get('registro_oficial') or '').split('.')[0] or reg
    return Candidate(type=t, registro_oficial=reg, record_key=rk,
                     doc_url=c.get('doc_url'), isin=c.get('isin'))


man = json.load(open(LK, encoding='utf-8'))
rows = []
for c in man['cases']:
    src = src_for(c['source_key'])
    cand = cand_for(c['candidate'])
    r = link(src, cand, kb)
    rows.append({'case_key': c['case_key'], 'stratum': c['stratum'],
                 'source_key': c['source_key'],
                 'candidate': c['candidate'],
                 'decision': r.decision.value, 'relation': r.relation,
                 'rule_id': r.rule_id,
                 'positive_evidence': r.positive_evidence,
                 'negative_evidence': r.negative_evidence})

payload = {'phase': 'G1-C linkage holdout predictions (sealed pre-scoring)',
           'code_freeze': 'a1da72a',
           'manifest': LK, 'n_cases': len(rows), 'predictions': rows}
OUT.parent.mkdir(parents=True, exist_ok=True)
json.dump(payload, open(OUT, 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
h = hashlib.sha256(OUT.read_bytes()).hexdigest()
print('n=', len(rows), 'sha256:', h)
from collections import Counter
print(Counter(r['decision'] for r in rows))
