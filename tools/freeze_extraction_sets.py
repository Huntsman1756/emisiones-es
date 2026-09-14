"""Descarga y congela los documentos del corpus de extraccion G0-B.

Produce g0/manifests/extraction-scout.json y extraction-holdout.json,
guardando los PDFs en g0/snapshots/ (gitignored) y registrando sha256,
status, content_type y retrieved_at por documento.
"""
import json, hashlib, datetime, time, random
import urllib.request, http.cookiejar
from pathlib import Path
from html import unescape
from collections import defaultdict

W = Path('.work')
SNAP = Path('g0/snapshots'); SNAP.mkdir(parents=True, exist_ok=True)
OUT = Path('g0/manifests')
SEED = 20260914
rng = random.Random(SEED + 1)

obs = json.load(open(W / 'observations.json', encoding='utf-8'))
fol, ccff, adm = obs['folletos'], obs['ccff'], obs['admisiones']
for f in fol + adm:
    f['denominacion'] = unescape(f['denominacion'])
for c in ccff:
    c['tipo_valor'] = unescape(c['tipo_valor'])

SCOUT_REGS = {'11400', '11424', '11425', '11426', '11431', '11433', '11434',
              '11437', '11436', '11422', '11421', '11420', '11419', '11417',
              '11365', '11316', '11319', '11303', '11416'}
SCOUT_CCFF = {'CCFF_11400_043', 'CCFF_11400_044', 'CCFF_11400_045',
              'CCFF_11400_034', 'CCFF_11425_001', 'CCFF_11431_001',
              'CCFF_11433_004', 'CCFF_11433_006', 'CCFF_11433_008'}
SCOUT_ADM = {f'ADM_{x}' for x in (143237, 143235, 143233, 143231, 143229, 143227, 143225, 143223)}

def scout(o):
    if o['family'] == 'cnmv_ccff':
        return o['source_record_key'] in SCOUT_CCFF or o['registro_oficial'] in SCOUT_REGS
    if o['family'] == 'cnmv_admision':
        return o['source_record_key'] in SCOUT_ADM
    return o['registro_oficial'] in SCOUT_REGS

fol_h = [o for o in fol if not scout(o)]
ccff_h = [o for o in ccff if not scout(o)]
adm_h = [o for o in adm if not scout(o)]

def pick(pool, n, key=None, distinct_issuers=True):
    pool = list(pool); rng.shuffle(pool)
    seen, out = set(), []
    for o in pool:
        if distinct_issuers and o['emisor'] in seen:
            continue
        seen.add(o['emisor']); out.append(o)
        if len(out) == n: break
    return out

def mk(o, case_key, stratum, role, iclass, reason, doc_url=None):
    return {'case_key': case_key, 'stratum': stratum,
            'issuer': o.get('emisor', ''), 'document_role': role,
            'instrument_class': iclass,
            'source_family': o['family'],
            'source_record_key': o['source_record_key'],
            'registro_oficial': o.get('registro_oficial'),
            'source_url': doc_url if doc_url is not None else o.get('doc_url'),
            'selection_reason': reason, 'downloaded': None}

cases = []
simp = [o for o in ccff_h if 'SIMPLES' in o['tipo_valor'] and o['doc_url']]
v5 = pick(simp, 5)
for i, o in enumerate(v5):
    cases.append(mk(o, f'X{i+1:02d}', 'plain_vanilla', 'final_terms',
                    'bono_simple', 'CCFF tipo BONOS/OBLIG. SIMPLES, emisores distintos'))
rest = [o for o in simp if o['source_record_key'] not in {c['source_record_key'] for c in cases}]
for i, o in enumerate(pick(rest, 4, distinct_issuers=False)):
    cases.append(mk(o, f'X{i+6:02d}', 'coupon_variant_candidate', 'final_terms',
                    'bono_simple_candidato_cupon_variable',
                    'segundo lote de bonos simples; candidatos FRN/variable no determinable desde superficie'))
ced = [o for o in ccff_h if 'CÉDULAS' in o['tipo_valor'] or 'CEDULAS' in o['tipo_valor'].upper()]
hip = [o for o in ced if 'HIPOTECARIAS' in o['tipo_valor'].upper()]
intl = [o for o in ced if 'INTERNACIONALIZA' in o['tipo_valor'].upper()]
sel = pick(hip, 3) + pick(intl, 3)[:1]
for i, o in enumerate(sel[:4]):
    cases.append(mk(o, f'X{i+10:02d}', 'covered_bond', 'final_terms', 'cedula',
                    'CCFF tipo CEDULAS (hipotecaria/internacionalizacion)'))
sub = [o for o in ccff_h if 'SUBORDINADOS' in o['tipo_valor'].upper()]
for i, o in enumerate(pick(sub, 2)):
    cases.append(mk(o, f'X{i+14:02d}', 'subordinated', 'final_terms', 'subordinado',
                    'CCFF tipo BONOS/OBLIG. SUBORDINADOS'))
est = [o for o in ccff_h if 'ESTRUCTURADOS' in o['tipo_valor'].upper()]
for i, o in enumerate(pick(est, 5, distinct_issuers=False)):
    cases.append(mk(o, f'X{i+16:02d}', 'structured', 'final_terms', 'estructurado',
                    'CCFF tipo BONOS/OBLIG. ESTRUCTURADOS'))
sups = [o for o in fol_h if o['rol'] == 'SUPLEMENTO']
for i, o in enumerate(pick(sups, 3)):
    cases.append(mk(o, f'X{i+21:02d}', 'supplement', 'supplement', 'n/a',
                    'registro con sufijo .k bajo rol SUPLEMENTO'))
mods = [o for o in fol if 'MODIFICACI' in o['rol']][:2]
for i, o in enumerate(mods):
    cases.append(mk(o, f'X{i+24:02d}', 'correction', 'correction', 'n/a',
                    'rol MODIFICACION con sufijo -k'))
dru = [o for o in fol_h if o['rol'] == 'DOC. REGISTRO UNIVERSAL']
cases.append(mk(pick(dru, 1)[0], 'X26', 'registration_document', 'registration_doc',
                'dru', 'rol DOC. REGISTRO UNIVERSAL'))
fta = [o for o in fol_h if o['rol'] == 'TOTAL FTA']
cases.append(mk(pick(fta, 1)[0], 'X27', 'securitisation', 'base_prospectus',
                'fta', 'rol TOTAL FTA'))
adebt = [o for o in adm_h if 'AIAF' in o['mercados'] and o['doc_url']]
cases.append(mk(adebt[0], 'X28', 'admission_debt', 'admission_doc', 'deuda',
                'folleto de admision mercado AIAF'))
aeq = [o for o in adm_h if 'AIAF' not in o['mercados'] and o['doc_url']]
cases.append(mk(aeq[0], 'X29', 'admission_equity', 'admission_doc', 'equity',
                'folleto de admision mercados bolsas'))
pag = [o for o in fol_h if 'PAGARES' in o['rol']]
cases.append(mk(pag[0], 'X30', 'commercial_paper_programme', 'base_prospectus',
                'pagares', 'rol PROGRAMA PAGARES'))

print('holdout cases:', len(cases))
assert len(cases) == 30

# ---- scout ----
def keyfind(pool, k, rol=None):
    return next(o for o in pool
                if o['source_record_key'] == k and (rol is None or o.get('rol') == rol))

scases = []
for k, stratum, role, icl in [
        ('CCFF_11400_043', 'scout_ccff', 'final_terms', 'bono_simple'),
        ('CCFF_11400_045', 'scout_ccff', 'final_terms', 'bono_simple'),
        ('CCFF_11425_001', 'scout_ccff_edge', 'final_terms', 'base_folleto_no_visible'),
        ('CCFF_11431_001', 'scout_ccff', 'final_terms', 'cedula'),
        ('CCFF_11433_008', 'scout_ccff', 'final_terms', 'estructurado')]:
    o = keyfind(ccff, k)
    scases.append(mk(o, f'Y{len(scases)+1:02d}', stratum, role, icl, 'discovery probe del brief'))
for k, stratum, role, icl, *rol in [
        ('FOL_11400', 'scout_folleto', 'base_prospectus', 'programa_rf'),
        ('FOL_11425.1', 'scout_suplemento', 'supplement', 'n/a'),
        ('FOL_11434', 'scout_fta', 'base_prospectus', 'fta', 'TOTAL FTA'),
        ('FOL_11417', 'scout_dru', 'registration_doc', 'dru')]:
    o = keyfind(fol, k, rol[0] if rol else None)
    scases.append(mk(o, f'Y{len(scases)+1:02d}', stratum, role, icl, 'inspeccionado durante discovery'))
o = keyfind(adm, 'ADM_143231')
scases.append(mk(o, 'Y10', 'scout_admision', 'admission_doc', 'equity',
                 'inspeccionado durante discovery; fila con enlace directo a documento'))
scases.append({'case_key': 'Y11', 'stratum': 'scout_portfolio',
               'issuer': 'AC RESIDENCIAL SOCIMI, S.A.', 'document_role': 'issue_document',
               'instrument_class': 'equity_socimi', 'source_family': 'portfolio_exchange',
               'source_record_key': 'PSE_ACRS_DOC_2589', 'registro_oficial': None,
               'source_url': 'https://api.portfolio.exchange/poex/document/2589',
               'selection_reason': 'Documento de Emision publicado en ficha de instrumento Portfolio',
               'downloaded': None})
print('scout cases:', len(scases))

# ---- descarga ----
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [('User-Agent', 'Mozilla/5.0 (research; emisiones-es G0-B)'),
                 ('Referer', 'https://www.cnmv.es/')]

PRE = {  # ya descargados en discovery
    'FOL_11400': '.work/doc_11400.pdf',
    'PSE_ACRS_DOC_2589': '.work/portfolio_doc2589.bin',
}
results = []
def fetch(c):
    url = c['source_url']
    if not url:
        c['downloaded'] = {'status': 'NO_DOC_URL'}; return
    rec = {'url': url, 'retrieved_at': datetime.datetime.utcnow().isoformat() + 'Z'}
    local = PRE.get(c['source_record_key'])
    if local:
        data = open(local, 'rb').read()
        rec.update(status=200, content_type='application/pdf', note='reused discovery download')
    else:
        try:
            if 'portfolio.exchange' in url:
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://portfolio.exchange/'})
                r = op.open(req, timeout=90)
            else:
                r = op.open(url, timeout=90)
            data = r.read()
            rec.update(status=r.status, content_type=r.headers.get('Content-Type'),
                       etag=r.headers.get('ETag'), last_modified=r.headers.get('Last-Modified'))
        except Exception as e:
            rec.update(status='ERR', error=str(e)[:200]); c['downloaded'] = rec
            results.append(rec); return
        time.sleep(0.7)
    rec['bytes'] = len(data)
    rec['sha256'] = hashlib.sha256(data).hexdigest()
    rec['is_pdf'] = data[:5] == b'%PDF-'
    fn = SNAP / f"{c['case_key']}_{c['source_record_key'].replace('/','_')}.pdf"
    fn.write_bytes(data)
    rec['local_evidence'] = str(fn)
    c['downloaded'] = rec
    results.append(rec)

for c in cases + scases:
    fetch(c)
ok = sum(1 for c in cases + scases if (c['downloaded'] or {}).get('is_pdf'))
print('pdfs ok:', ok, '/', len(cases) + len(scases))
for c in cases + scases:
    d = c['downloaded'] or {}
    print(f" {c['case_key']:>4} {d.get('status','-'):>4} {d.get('bytes','-'):>8} {str(d.get('is_pdf')):>5} {c['source_record_key']} {c['issuer'][:38]}")

def wm(name, cs, extra):
    doc = {'manifest': name, 'frozen_at': '2026-09-14', 'seed': SEED,
           'storage': 'PDFs en g0/snapshots/ (gitignored); identidad = source_url + sha256 + retrieved_at',
           'n_cases': len(cs), 'cases': cs, **extra}
    p = json.dumps(doc, ensure_ascii=False, sort_keys=True).encode()
    doc['manifest_sha256'] = hashlib.sha256(p).hexdigest()
    json.dump(doc, open(OUT / name, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return doc['manifest_sha256']

hs = wm('extraction-holdout.json', cases,
        {'sampling_rule': 'estratos del corpus-proposal sobre pools holdout (registros no inspeccionados en discovery); seed 20260914'})
ss = wm('extraction-scout.json', scases,
        {'sampling_rule': 'documentos inspeccionados durante discovery G0-B; libre uso para diseno de extractores'})
json.dump(results, open(W / 'pdf_fetches.json', 'w'), ensure_ascii=False, indent=1)
print('holdout sha', hs[:16], '| scout sha', ss[:16])
