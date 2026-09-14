"""Genera los manifests congelados de G0-B a partir de las observaciones
crudas adquiridas en .work/.

Uso: python tools/build_g0b_manifests.py
Determinista: seed fija, sin lectura de PDFs de holdout.
"""
import json, re, hashlib, datetime
from pathlib import Path
from collections import defaultdict

W = Path('.work')
OUT = Path('g0/manifests')
SEED = 20260914

def load(p):
    for enc in ('utf-8', 'cp1252', 'latin-1'):
        try:
            return json.load(open(W / p, encoding=enc))
        except Exception:
            pass
    raise RuntimeError(p)

# ---------- normalización ----------
def norm_folleto(r, year):
    c = r['cells']
    reg = c[1]
    base = re.split(r'[.\-]', reg)[0]
    suffix = reg[len(base):] or None
    role = re.sub(r'&[^;]+;', ' ', c[5]).strip().upper()
    doc = next((l for l in r['links'] if 'verdocumento' in l), None)
    nif = next((re.search(r'nif=([A-Z0-9]+)', l).group(1)
                for l in r['links'] if 'nif=' in l), None)
    return {'family': 'cnmv_folletos_emision', 'source_record_key': f'FOL_{reg}',
            'registro_oficial': base, 'version_suffix': suffix, 'rol': role,
            'emisor': c[2], 'nif': nif, 'fecha_registro': c[0],
            'denominacion': c[5], 'nominal': c[6] if len(c) > 6 else '',
            'isin': c[7] if len(c) > 7 else '', 'admision': c[8] if len(c) > 8 else '',
            'doc_url': ('https://www.cnmv.es/webservices/verdocumento/ver?e=' + doc.split('e=')[-1]) if doc else None,
            'year': year}

def norm_ccff(r):
    c = r['cells']
    # search-table: [finalidad,pres,ultmod,nreg,emisor,freg,regof,doc,tipo,nominal,isin,adm]
    doc = next((l for l in r['links'] if 'verdocumento' in l), None)
    numfol = next((re.search(r'NUMFOL=(\d+)', l).group(1)
                   for l in r['links'] if 'NUMFOL=' in l), None)
    return {'family': 'cnmv_ccff', 'source_record_key': c[3],
            'finalidad': c[0], 'presentacion': c[1], 'ult_mod': c[2],
            'emisor': c[4], 'fecha_reg': c[5], 'registro_oficial': c[6],
            'numfol_link': numfol, 'doc_url': ('https://www.cnmv.es/webservices/verdocumento/ver?e=' + doc.split('e=')[-1]) if doc else None,
            'tipo_valor': c[8], 'nominal': c[9], 'isin': c[10], 'admision': c[11]}

def norm_adm(r):
    c = r['cells']
    doc = next((l for l in r['links'] if 'verdocumento' in l), None)
    return {'family': 'cnmv_admision', 'source_record_key': f'ADM_{c[1]}',
            'registro_oficial': c[1], 'emisor': c[2], 'fecha_registro': c[0],
            'denominacion': c[5], 'nominal': c[6], 'isin': c[7] if len(c) > 7 else '',
            'mercados': c[8] if len(c) > 8 else '',
            'doc_url': ('https://www.cnmv.es/webservices/verdocumento/ver?e=' + doc.split('e=')[-1]) if doc else None}

fol, ccff, adm = [], [], []
for yr in (2021, 2022, 2023, 2024, 2025, 2026):
    fol += [norm_folleto(r, yr) for r in load(f'folletos_{yr}_raw.json')]
for yr in (2023, 2024, 2025, 2026):
    ccff += [norm_ccff(r) for r in load(f'ccff_{yr}_raw.json')]
adm = [norm_adm(r) for r in load('admision_raw.json')]

# ---------- pools ----------
# Registros inspeccionados durante discovery → SCOUT (contaminados para holdout)
SCOUT_REGS = {'11400', '11424', '11425', '11426', '11431', '11433', '11434',
              '11437', '11436', '11422', '11421', '11420', '11419', '11417',
              '11365', '11316', '11319', '11303', '11416'}
SCOUT_CCFF = {'CCFF_11400_043', 'CCFF_11400_044', 'CCFF_11400_045',
              'CCFF_11400_034', 'CCFF_11425_001', 'CCFF_11431_001',
              'CCFF_11433_004', 'CCFF_11433_006', 'CCFF_11433_008'}
SCOUT_ADM = {'ADM_143237', 'ADM_143235', 'ADM_143233', 'ADM_143231',
             'ADM_143229', 'ADM_143227', 'ADM_143225', 'ADM_143223'}

def in_scout(o):
    if o['family'] == 'cnmv_ccff':
        return o['source_record_key'] in SCOUT_CCFF or o['registro_oficial'] in SCOUT_REGS
    if o['family'] == 'cnmv_admision':
        return o['source_record_key'] in SCOUT_ADM
    return o['registro_oficial'] in SCOUT_REGS

fol_s, fol_h = [o for o in fol if in_scout(o)], [o for o in fol if not in_scout(o)]
ccff_s, ccff_h = [o for o in ccff if in_scout(o)], [o for o in ccff if not in_scout(o)]
adm_s, adm_h = [o for o in adm if in_scout(o)], [o for o in adm if not in_scout(o)]
print(f'pools: fol scout {len(fol_s)} holdout {len(fol_h)} | '
      f'ccff scout {len(ccff_s)} holdout {len(ccff_h)} | adm scout {len(adm_s)} holdout {len(adm_h)}')

import random
rng = random.Random(SEED)

cases = []

def ck(prefix, n): return f'{prefix}-{n:03d}'

def case(ck_, stratum, src, cand, label, rel, evidence, label_source='structural'):
    return {'case_key': ck_, 'stratum': stratum,
            'source': {'family': src['family'], 'record_key': src['source_record_key'],
                       'registro_oficial': src.get('registro_oficial'),
                       'doc_url': src.get('doc_url'), 'isin': src.get('isin')},
            'candidate': cand, 'label': label, 'relation_if_exact': rel,
            'label_source': label_source, 'evidence': evidence, 'notes': ''}

# ---- HOLDOUT ----
H = []
# S1: CCFF -> base folleto (EXACT via reg_oficial/NUMFOL link)
pool = [o for o in ccff_h if o['doc_url']]
rng.shuffle(pool)
for i, o in enumerate(pool[:98]):
    H.append(case(ck('S1', i + 1), 'S1_final_terms_to_programme', o,
                  {'type': 'folleto', 'registro_oficial': o['registro_oficial'],
                   'url': f"https://www.cnmv.es/portal/consultas/folletos/folletosemisionopv.aspx?NUMFOL={o['registro_oficial']}"},
                  'EXACT_LINK', 'DEFINES_TERMS_FOR',
                  'fila CCFF enlaza explicitamente NUMFOL=registro_oficial'))
# S2: suplemento -> folleto base (EXACT via sufijo .k)
sup_h = [o for o in fol_h if o['rol'] == 'SUPLEMENTO']
rng.shuffle(sup_h)
for i, o in enumerate(sup_h[:50]):
    H.append(case(ck('S2', i + 1), 'S2_supplement_to_prospectus', o,
                  {'type': 'folleto', 'registro_oficial': o['registro_oficial'],
                   'url': f"https://www.cnmv.es/portal/consultas/folletos/folletosemisionopv.aspx?NUMFOL={o['registro_oficial']}"},
                  'EXACT_LINK', 'SUPPLEMENTS',
                  'registro X.k referencia al folleto base X'))
# S3: modificacion -> documento corregido
# Las 6 modificaciones observadas van todas a holdout (excluidas de scout para
# no duplicar la misma decision en ambos conjuntos)
mod_all = [o for o in fol if 'MODIFICACI' in o['rol']]
for i, o in enumerate(mod_all):
    H.append(case(ck('S3', i + 1), 'S3_correction_to_document', o,
                  {'type': 'folleto', 'registro_oficial': o['registro_oficial'],
                   'url': f"https://www.cnmv.es/portal/consultas/folletos/folletosemisionopv.aspx?NUMFOL={o['registro_oficial']}"},
                  'EXACT_LINK', 'CORRECTS',
                  'registro X-k modifica folleto X'))
# S3 rest: modificacion emparejada con folleto ajeno -> NO_LINK
wrong = [o for o in fol_h if o['rol'].startswith('PROGRAMA')]
rng.shuffle(wrong)
for i, o in enumerate(mod_all[:4]):
    w = wrong[i]
    H.append(case(ck('S3', len(mod_all) + i + 1), 'S3_correction_to_document', o,
                  {'type': 'folleto', 'registro_oficial': w['registro_oficial'],
                   'url': f"https://www.cnmv.es/portal/consultas/folletos/folletosemisionopv.aspx?NUMFOL={w['registro_oficial']}"},
                  'NO_LINK', None,
                  'modificacion de emisor X emparejada con folleto de emisor Y'))
# S4: sucesion anual de programa (issuer -> programa consecutivo anterior)
byiss = defaultdict(list)
for o in fol_h:
    if o['rol'] in ('PROGRAMA RENTA FIJA', 'DOC. REGISTRO UNIVERSAL', 'DOC. REGISTRO'):
        byiss[o['emisor']].append(o)
succ = []
for iss, lst in byiss.items():
    lst.sort(key=lambda o: int(o['registro_oficial']))
    for a, b in zip(lst, lst[1:]):
        if a['rol'] == b['rol']:
            succ.append((b, a))
rng.shuffle(succ)
for i, (new, prev) in enumerate(succ[:25]):
    H.append(case(ck('S4', i + 1), 'S4_programme_succession', new,
                  {'type': 'folleto', 'registro_oficial': prev['registro_oficial'],
                   'url': f"https://www.cnmv.es/portal/consultas/folletos/folletosemisionopv.aspx?NUMFOL={prev['registro_oficial']}"},
                  'EXACT_LINK', 'REPLACES',
                  'mismo emisor, mismo rol, registro consecutivo (renovacion anual)'))
# S5: admision -> security (EXACT via ISIN)
adm_i = [o for o in adm_h if re.match(r'^[A-Z]{2}[0-9A-Z]{10}$', o['isin'] or '')]
rng.shuffle(adm_i)
for i, o in enumerate(adm_i[:35]):
    H.append(case(ck('S5', i + 1), 'S5_admission_to_security', o,
                  {'type': 'security', 'isin': o['isin']},
                  'EXACT_LINK', 'ADMISSION_OF',
                  'fila de admision porta ISIN explicito'))
# S6: mismo emisor, programa equivocado -> NO_LINK
ccff_byiss = defaultdict(list)
for o in ccff_h: ccff_byiss[o['emisor']].append(o)
s6 = []
for iss, lst in ccff_byiss.items():
    progs = [o for o in fol if o['emisor'] == iss and o['rol'].startswith(('PROGRAMA', 'DOC'))]
    others = [p for p in progs if p['registro_oficial'] not in {c['registro_oficial'] for c in lst}]
    for c in lst:
        for p in others:
            s6.append((c, p))
rng.shuffle(s6)
for i, (c, p) in enumerate(s6[:15]):
    H.append(case(ck('S6', i + 1), 'S6_same_issuer_wrong_programme', c,
                  {'type': 'folleto', 'registro_oficial': p['registro_oficial'],
                   'url': f"https://www.cnmv.es/portal/consultas/folletos/folletosemisionopv.aspx?NUMFOL={p['registro_oficial']}"},
                  'NO_LINK', None,
                  'mismo emisor, distinto programa/registro'))
# S7: mismo programa, rol documental distinto -> NO_LINK doc-doc
# (suplemento X.k y CCFF de X son documentos hermanos; no existe arista
# doc-doc definida entre ellos)
sup_h_all = [o for o in fol_h if o['rol'] == 'SUPLEMENTO']
ccff_byreg = defaultdict(list)
for o in ccff_h:
    ccff_byreg[o['registro_oficial']].append(o)
s7 = []
for s in sup_h_all:
    for c in ccff_byreg.get(s['registro_oficial'], [])[:1]:
        s7.append((c, s))
s7 = s7[:7]
for i, (c, s) in enumerate(s7):
    H.append(case(ck('S7', i + 1), 'S7_same_programme_different_role', c,
                  {'type': 'folleto_doc', 'record_key': s['source_record_key'],
                   'doc_url': s['doc_url'], 'rol': s['rol']},
                  'NO_LINK', None,
                  'mismo registro/programa pero arista doc-doc no definida '
                  '(suplemento->base existe; ccff->suplemento no)'))
# serie FTA: dos docs distintos, mismo ISIN -> NO_LINK doc-doc
seen_isin = set()
for a in fol_h:
    for b in fol_h:
        if (a['isin'] and a['isin'] == b['isin'] and a['source_record_key'] != b['source_record_key']
                and a['isin'] not in seen_isin):
            seen_isin.add(a['isin'])
            s7b = a
            H.append(case(ck('S7', len(s7) + 1), 'S7_same_programme_different_role', a,
                          {'type': 'folleto_doc', 'record_key': b['source_record_key'],
                           'doc_url': b['doc_url'], 'rol': b['rol']},
                          'NO_LINK', None,
                          'mismo ISIN, documentos serie distintos; arista doc-doc no definida'))
            break
# S8: titulo similar, emisor distinto -> NO_LINK
s8 = []
progs_all = [o for o in fol_h if o['rol'] == 'PROGRAMA RENTA FIJA']
for c in ccff_h[:200]:
    for p in progs_all:
        if p['emisor'] != c['emisor'] and p['registro_oficial'] != c['registro_oficial']:
            s8.append((c, p))
rng.shuffle(s8)
for i, (c, p) in enumerate(s8[:15]):
    H.append(case(ck('S8', i + 1), 'S8_similar_title_diff_issuer', c,
                  {'type': 'folleto', 'registro_oficial': p['registro_oficial'],
                   'emisor': p['emisor'],
                   'url': f"https://www.cnmv.es/portal/consultas/folletos/folletosemisionopv.aspx?NUMFOL={p['registro_oficial']}"},
                  'NO_LINK', None,
                  'denominacion identica (PROGRAMA RENTA FIJA), emisor distinto'))
# S9: no-link / evidencia insuficiente
s9 = []
# series de FTA: la fila serie no tiene doc propio -> enlace doc-doc no resoluble
series = [o for o in fol_h if o['rol'].startswith('SERIE')]
rng.shuffle(series)
for o in series[:20]:
    s9.append((o, 'SERIE row sin doc_url propio; ISIN propio pero documento no observable por separado'))
# folletos sin doc_url
nodoc = [o for o in fol_h if not o['doc_url'] and o['rol'] != 'SERIE']
for o in nodoc[:10]:
    s9.append((o, 'registro sin enlace de documento observable'))
for i, (o, why) in enumerate(s9[:24]):
    H.append(case(ck('S9', i + 1), 'S9_no_link_insufficient', o, {'type': 'none'},
                  'NO_LINK' if o['rol'].startswith('SERIE') else 'AMBIGUOUS', None, why))
# S10: multi-venue (admisiones con varios mercados / FTA sin admision)
s10 = []
mv = [o for o in adm_h if ' ' in (o['mercados'] or '').strip()]
for o in mv[:10]:
    s10.append((o, {'type': 'security', 'isin': o['isin']}, 'EXACT_LINK', 'ADMISSION_OF',
                f"admision multisede {o['mercados']}"))
fta_noadm = [o for o in fol_h if o['admision'] in ('No', '') and o['rol'].startswith('SERIE')]
for o in fta_noadm[:5]:
    s10.append((o, {'type': 'venue', 'value': 'ANY'}, 'NO_LINK', None,
                'serie FTA marcada No admision -> sin venue'))
for i, (o, cand, lab, rel, ev) in enumerate(s10[:15]):
    H.append(case(ck('S10', i + 1), 'S10_multi_venue', o, cand, lab, rel, ev))
# S11: ambiguous ground truth (registro 11425 reservado a holdout; scout no lo usa)
s11src = []
for o in fol:
    if o['registro_oficial'] == '11425':
        s11src.append((o, 'base 11425 no visible en detalle (solo suplemento); evidencia parcial'))
# registro con esquema 2026xxxxx (familia distinta)
amb2 = [o for o in fol_h if o['registro_oficial'].startswith('2026') and o['rol'] == 'SERIE']
for o in amb2[:4]:
    s11src.append((o, 'serie bajo esquema de registro 2026xxxxx; relacion doc-doc no demostrable desde superficie'))
# CCFF con mismo ISIN (ampliacion/reapertura): supresion no determinable
# desde la superficie sin leer documentos -> AMBIGUOUS
from collections import Counter as _C
_isincnt = _C(c['isin'] for c in ccff_h if c['isin'])
for isin, n in _isincnt.items():
    if n > 1:
        rows = [c for c in ccff_h if c['isin'] == isin]
        for a, b in zip(rows, rows[1:]):
            s11src.append((a, f'dos CCFF comparten ISIN {isin}; supersession no determinable',
                           {'type': 'ccff_doc', 'record_key': b['source_record_key'],
                            'doc_url': b['doc_url']}))
for i, item in enumerate(s11src[:10]):
    o, why = item[0], item[1]
    cand = item[2] if len(item) > 2 else {'type': 'unknown'}
    H.append(case(ck('S11', i + 1), 'S11_ambiguous_ground_truth', o,
                  cand, 'AMBIGUOUS', None, why, label_source='manual'))

print('holdout total:', len(H))

# ---- SCOUT (55) ----
S = []
for i, o in enumerate([o for o in ccff_s if o['doc_url']]):
    S.append(case(ck('T1', i + 1), 'scout_ccff_to_programme', o,
                  {'type': 'folleto', 'registro_oficial': o['registro_oficial'],
                   'url': f"https://www.cnmv.es/portal/consultas/folletos/folletosemisionopv.aspx?NUMFOL={o['registro_oficial']}"},
                  'EXACT_LINK', 'DEFINES_TERMS_FOR', 'CCFF->NUMFOL explicito'))
sup_s = [o for o in fol_s if o['rol'] == 'SUPLEMENTO']
for i, o in enumerate(sup_s):
    S.append(case(ck('T2', i + 1), 'scout_supplement', o,
                  {'type': 'folleto', 'registro_oficial': o['registro_oficial'],
                   'url': f"https://www.cnmv.es/portal/consultas/folletos/folletosemisionopv.aspx?NUMFOL={o['registro_oficial']}"},
                  'EXACT_LINK', 'SUPPLEMENTS', 'registro X.k -> X'))
# las modificaciones van solo a holdout (ver S3); scout no las repite
for i, o in enumerate(adm_s[:12]):
    S.append(case(ck('T4', i + 1), 'scout_admission', o,
                  {'type': 'security', 'isin': o['isin']}, 'EXACT_LINK', 'ADMISSION_OF',
                  'admision con ISIN explicito'))
# scout hard negatives: Santander CCFF vs Santander otro programa
sn = [o for o in ccff_s if 'SANTANDER' in o['emisor']]
for i, o in enumerate(sn[:6]):
    S.append(case(ck('T5', i + 1), 'scout_same_issuer_wrong_programme', o,
                  {'type': 'folleto', 'registro_oficial': '11437'},
                  'NO_LINK', None, 'CCFF_11400_x vs programa 11437 del mismo emisor'))
# scout ambiguous: FTA serie sin doc propio (ya cubierto por T7); el caso
# 11425 (base invisible) queda reservado al holdout S11
serie_s = [o for o in fol_s if o['rol'].startswith('SERIE')]
for i, o in enumerate(serie_s[:6]):
    S.append(case(ck('T7', i + 1), 'scout_serie_no_doc', o, {'type': 'none'},
                  'NO_LINK', None, 'fila serie sin doc propio'))
# portfolio equity admission (doc de emision existe via api.portfolio.exchange)
S.append({'case_key': 'T8-001', 'stratum': 'scout_portfolio_equity',
          'source': {'family': 'portfolio_exchange', 'record_key': 'PSE_ACRS',
                     'registro_oficial': None,
                     'doc_url': 'https://api.portfolio.exchange/poex/document/2589',
                     'isin': 'ES0105746004'},
          'candidate': {'type': 'security', 'isin': 'ES0105746004'},
          'label': 'EXACT_LINK', 'relation_if_exact': 'DEFINES_TERMS_FOR',
          'label_source': 'structural',
          'evidence': 'pagina instrumento portfolio.exchange lista Documento de Emision',
          'notes': 'Documento de Emision - AC Residencial (2024-06-26); requiere header Referer'})

print('scout total:', len(S))

def write_manifest(name, cases_, extra):
    doc = {'manifest': name, 'frozen_at': '2026-09-14', 'seed': SEED,
           'label_policy': 'labels assigned by construction from CNMV record structure; '
                           'AMBIGUOUS cases marked manual; never auto-promote AMBIGUOUS',
           'n_cases': len(cases_), 'cases': cases_, **extra}
    payload = json.dumps(doc, ensure_ascii=False, sort_keys=True).encode('utf-8')
    doc['manifest_sha256'] = hashlib.sha256(payload).hexdigest()
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(doc, open(OUT / name, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return doc['manifest_sha256']

h_sha = write_manifest('linkage-holdout.json', H, {
    'sampling_rule': 'stratified by construction over acquired CNMV rows 2022-2026; '
                     'scout-source registros excluded; rng seed 20260914',
    'strata_counts': {s: sum(1 for c in H if c['stratum'] == s) for s in {c['stratum'] for c in H}}})
s_sha = write_manifest('linkage-scout.json', S, {
    'sampling_rule': 'records manually inspected during G0-B discovery phase; '
                     'free to use for rule design; disjoint from holdout',
    'strata_counts': {s: sum(1 for c in S if c['stratum'] == s) for s in {c['stratum'] for c in S}}})

# normalized observation store (resumen, sin HTML crudo)
obs = {'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
       'counts': {'folletos': len(fol), 'ccff': len(ccff), 'admisiones': len(adm)},
       'folletos': fol, 'ccff': ccff, 'admisiones': adm}
json.dump(obs, open(W / 'observations.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('holdout sha:', h_sha[:16], '| scout sha:', s_sha[:16])
