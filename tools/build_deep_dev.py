"""G0-C.1: construye y congela extraction-deep-dev (development).

Seleccion estructural desde .work/observations.json: NO se lee ningun
contenido de documento para decidir la inclusion. Excluye toda clave ya
usada en scout/holdout (linkage y extraction) y en ambiguity-dev.

Estratos buscados (si existen en el pool libre):
  structured_note      CCFF tipo BONOS/OBLIG. ESTRUCTURADOS
  subordinated         CCFF tipo BONOS/OBLIG. SUBORDINADOS
  plain_vanilla        CCFF tipo BONOS/OBLIG. SIMPLES
  covered_bond         CCFF tipo CEDULAS
  supplement           folleto rol SUPLEMENTO (.k)
  modification         folleto rol MODIFICACION (-k)

Los PDFs se guardan en g0/snapshots/ con prefijo D (gitignored, como X/Y)
y el manifest registra source_url + sha256 + retrieved_at.
"""
import datetime
import hashlib
import http.cookiejar
import json
import time
import urllib.request
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / 'g0/snapshots'
OUT = ROOT / 'g0/manifests/extraction-deep-dev.json'

obs = json.load(open(ROOT / '.work/observations.json', encoding='utf-8'))

# ---------- exclusion: solo membresia de claves, nunca contenido ----------
used = set()
for p in ('g0/manifests/linkage-scout.json',
          'g0/manifests/linkage-holdout.json',
          'g0/manifests/extraction-scout.json',
          'g0/manifests/extraction-holdout.json',
          'g0/linkage-ambiguity-dev/cases.json'):
    m = json.load(open(ROOT / p, encoding='utf-8'))
    for c in m['cases']:
        for d in (c.get('source') or {}, c.get('candidate') or {}, c):
            for kk in ('record_key', 'source_record_key', 'doc_key', 'key'):
                if d.get(kk):
                    used.add(d[kk])
for f in SNAP.iterdir():
    parts = f.name.split('_', 1)
    if len(parts) == 2:
        used.add(parts[1].rsplit('.', 1)[0])

ccff = [c for c in obs['ccff']
        if c['source_record_key'] not in used and c.get('doc_url')]
fol = [f for f in obs['folletos']
       if f['source_record_key'] not in used and f.get('doc_url')]

by_key = {c['source_record_key']: c for c in ccff}
by_key.update({f['source_record_key']: f for f in fol})

# ---------- seleccion (estructural; sin abrir documentos) ----------
PICKS = [
    # (record_key, stratum, document_role, instrument_class, target families)
    ('CCFF_11290_006', 'structured_note', 'final_terms', 'estructurado',
     ['underlying', 'barrier', 'participation', 'cap', 'observation_dates',
      'settlement_type', 'redemption_formula']),
    ('CCFF_11380_022', 'structured_note', 'final_terms', 'estructurado',
     ['underlying', 'barrier', 'participation', 'cap', 'observation_dates',
      'settlement_type', 'redemption_formula']),
    ('CCFF_11380_015', 'structured_note', 'final_terms', 'estructurado',
     ['underlying', 'barrier', 'participation', 'cap', 'observation_dates',
      'settlement_type', 'redemption_formula']),
    ('CCFF_11407_001', 'subordinated', 'final_terms', 'subordinado',
     ['ranking', 'subordination', 'call_dates', 'redemption_formula']),
    ('CCFF_11398_002', 'plain_vanilla', 'final_terms', 'bono_simple',
     ['call_dates', 'put_dates', 'benchmark', 'spread',
      'business_day_convention']),
    ('CCFF_11399_001', 'plain_vanilla', 'final_terms', 'bono_simple',
     ['call_dates', 'put_dates', 'benchmark', 'spread',
      'business_day_convention']),
    ('CCFF_11341_007', 'covered_bond', 'final_terms', 'cedula',
     ['call_dates', 'reset_dates', 'fixing_rules', 'benchmark', 'spread']),
    ('CCFF_11384_005', 'covered_bond', 'final_terms', 'cedula',
     ['call_dates', 'reset_dates', 'fixing_rules', 'benchmark', 'spread']),
    ('CCFF_11338_001', 'covered_bond', 'final_terms', 'cedula',
     ['call_dates', 'reset_dates', 'fixing_rules', 'benchmark', 'spread']),
    ('FOL_11145.1', 'supplement', 'supplement', 'n/a',
     ['supplement_changes_economic_terms']),
    ('FOL_11269.1', 'supplement', 'supplement', 'n/a',
     ['supplement_changes_economic_terms']),
    ('FOL_11260.1', 'supplement', 'supplement', 'n/a',
     ['supplement_changes_economic_terms']),
    ('FOL_11329.1', 'supplement', 'supplement', 'n/a',
     ['supplement_changes_economic_terms']),
]

cases = []
for i, (key, stratum, role, icl, fams) in enumerate(PICKS, 1):
    o = by_key[key]
    cases.append({
        'case_key': f'D{i:02d}', 'stratum': stratum,
        'issuer': unescape(o.get('emisor') or ''),
        'isin': o.get('isin'),
        'document_role': role, 'instrument_class': icl,
        'source_family': o['family'],
        'source_record_key': key,
        'registro_oficial': o.get('registro_oficial'),
        'source_url': o['doc_url'],
        'selection_reason':
            f'{stratum}: {o.get("tipo_valor") or o.get("rol")}; '
            'seleccion estructural sin inspeccion de contenido',
        'target_field_families': fams,
        'downloaded': None,
    })

# estratos sin representacion en el pool libre
declared_gaps = [
    {'stratum': 'modification', 'status': 'NO_DEV_EVIDENCE',
     'note': 'todos los folletos rol MODIFICACION con doc_url ya estan '
             'usados en scout/holdout; ninguno libre en el pool'},
    {'stratum': 'callable_explicit', 'status': 'NOT_DETERMINED_PRE',
     'note': 'ningun campo de superficie CNMV identifica callable; '
             'la presencia se descubre al abrir los docs development'},
]

# ---------- descarga ----------
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [('User-Agent', 'Mozilla/5.0 (research; emisiones-es G0-C.1)'),
                 ('Referer', 'https://www.cnmv.es/')]

for c in cases:
    rec = {'url': c['source_url'],
           'retrieved_at': datetime.datetime.now(
               datetime.timezone.utc).isoformat()}
    try:
        r = op.open(c['source_url'], timeout=90)
        data = r.read()
        rec.update(status=r.status,
                   content_type=r.headers.get('Content-Type'),
                   last_modified=r.headers.get('Last-Modified'))
        time.sleep(0.7)
        rec['bytes'] = len(data)
        rec['sha256'] = hashlib.sha256(data).hexdigest()
        rec['is_pdf'] = data[:5] == b'%PDF-'
        fn = SNAP / f"{c['case_key']}_{c['source_record_key']}.pdf"
        fn.write_bytes(data)
        rec['local_evidence'] = str(fn.relative_to(ROOT))
    except Exception as e:
        rec.update(status='ERR', error=str(e)[:200])
    c['downloaded'] = rec
    print(f" {c['case_key']:>4} {rec.get('status', '-'):>4} "
          f"{rec.get('bytes', '-'):>8} {rec.get('is_pdf')} "
          f"{c['source_record_key']} {c['issuer'][:38]}")

doc = {
    'manifest': 'extraction-deep-dev',
    'frozen_at': datetime.datetime.now(datetime.timezone.utc)
    .date().isoformat(),
    'purpose': 'DEVELOPMENT para segunda ola contractual; externo a '
               'scout y holdout; congelado antes de escribir reglas',
    'storage': 'PDFs en g0/snapshots/ (gitignored); identidad = '
               'source_url + sha256 + retrieved_at',
    'n_cases': len(cases),
    'cases': cases,
    'declared_gaps': declared_gaps,
}
payload = json.dumps(doc, ensure_ascii=False, sort_keys=True).encode()
doc['manifest_sha256'] = hashlib.sha256(payload).hexdigest()
json.dump(doc, open(OUT, 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
ok = sum(1 for c in cases if (c['downloaded'] or {}).get('is_pdf'))
print(f'\npdfs ok: {ok}/{len(cases)}  manifest sha: '
      f"{doc['manifest_sha256'][:16]}")
