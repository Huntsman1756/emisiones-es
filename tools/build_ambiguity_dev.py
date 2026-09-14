"""Construye g0/linkage-ambiguity-dev/cases.json: casos reales de
ambiguedad de linkage sobre registros CNMV que NO pertenecen ni al
scout ni al holdout (verificado por membresia de record_key).

Etiquetado manual permitido: es DEVELOPMENT. Nunca toca el holdout.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'g0/linkage-ambiguity-dev'
OUT.mkdir(parents=True, exist_ok=True)

# ---- membresia de records ya utilizados (scout + holdout) ----
used = set()
for f in ('linkage-holdout', 'linkage-scout'):
    m = json.load(open(ROOT / f'g0/manifests/{f}.json', encoding='utf-8'))
    for c in m['cases']:
        used.add(c['case_key'])
        def walk(x):
            if isinstance(x, str):
                for t in x.replace('(', ' ').replace(')', ' ').split():
                    if t.startswith(('CCFF_', 'FOL_', 'ADM_', 'PSE_')):
                        used.add(t)
            elif isinstance(x, dict):
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(c)

FOL = 'cnmv_folletos_emision'
CNMV_PORTAL = ('https://www.cnmv.es/portal/consultas/folletos/'
               'folletosemisionopv.aspx?NUMFOL=')


def fol(rec, reg, rol, fecha, emisor, isin=''):
    return {'family': FOL, 'record_key': f'FOL_{rec}',
            'registro_oficial': reg, 'rol': rol, 'fecha': fecha,
            'emisor': emisor, 'isin': isin}


def cand_fol(reg, version=None):
    c = {'type': 'folleto', 'registro_oficial': reg,
         'url': CNMV_PORTAL + reg}
    if version:
        c['version'] = version
    return c


def ccff(rec, reg, fecha, isin, emisor):
    # fecha = presentacion real de la CCFF (no fecha_reg del folleto)
    return {'family': 'cnmv_ccff', 'record_key': rec,
            'registro_oficial': reg, 'numfol_link': reg, 'fecha': fecha,
            'isin': isin, 'emisor': emisor}


def adm(rec, emisor, isin, fecha):
    return {'family': 'cnmv_admision', 'record_key': rec,
            'emisor': emisor, 'isin': isin, 'fecha': fecha}


CASES = [
    # ---------- sucesion de programa: mismo emisor+rol, distinto registro,
    # sin evidencia explicita de sustitucion -> AMBIGUOUS ----------
    dict(key='AMB-001', stratum='succession_unverified',
         source=fol('11199', '11199', 'PROGRAMA RENTA FIJA', '05/08/2021',
                    'BANCA MARCH, S.A.'),
         cand=cand_fol('11268'), label='AMBIGUOUS',
         notes='BANCA MARCH programa RF 2021 vs 2023: renovacion probable '
               'pero sin campo explicito de sucesion'),
    dict(key='AMB-002', stratum='succession_unverified',
         source=fol('11268', '11268', 'PROGRAMA RENTA FIJA', '18/04/2023',
                    'BANCA MARCH, S.A.'),
         cand=cand_fol('11398'), label='AMBIGUOUS',
         notes='BANCA MARCH 2023 vs 2025'),
    dict(key='AMB-003', stratum='succession_unverified',
         source=fol('11196', '11196', 'PROGRAMA RENTA FIJA', '15/07/2021',
                    'ABANCA CORPORACION BANCARIA, S.A.'),
         cand=cand_fol('11234'), label='AMBIGUOUS',
         notes='ABANCA 2021 vs 2022'),
    dict(key='AMB-004', stratum='succession_unverified',
         source=fol('11245', '11245', 'PROGRAMA RENTA FIJA', '21/07/2022',
                    'CAIXABANK, S.A.'),
         cand=cand_fol('11290'), label='AMBIGUOUS',
         notes='CAIXABANK 2022 vs 2023'),
    # control: emisor distinto -> NO_LINK
    dict(key='AMB-005', stratum='succession_unverified',
         source=fol('11245', '11245', 'PROGRAMA RENTA FIJA', '21/07/2022',
                    'CAIXABANK, S.A.'),
         cand=cand_fol('11268'), label='NO_LINK',
         notes='CAIXABANK vs BANCA MARCH: evidencia negativa emisor'),
    # ---------- serie FTA vs documento base: documentada en el folleto
    # pero terminos en CCFF; tipo de relacion no decidible ----------
    dict(key='AMB-006', stratum='serie_vs_base',
         source=fol('11202_SA', '11202', 'SERIE Serie A', '23/09/2021', 'FONDO DE TITULIZACION SANTANDER'),
         cand=cand_fol('11202'), label='AMBIGUOUS',
         notes='SERIE Serie A de FTA 11202 vs documento base'),
    dict(key='AMB-007', stratum='serie_vs_base',
         source=fol('11150_SC', '11150', 'SERIE Class C', '16/02/2021', 'SANTANDER CONSUMO 4, FONDO DE TITULIZACION'),
         cand=cand_fol('11150'), label='AMBIGUOUS',
         notes='SERIE Class C de FTA 11150 vs base'),
    dict(key='AMB-008', stratum='serie_vs_base',
         source=fol('11246_SD', '11246', 'SERIE Clase D', '22/09/2022', 'AUTONORIA SPAIN 2022, FONDO DE TITULIZACION'),
         cand=cand_fol('11246'), label='AMBIGUOUS',
         notes='SERIE Clase D de FTA 11246 vs base'),
    dict(key='AMB-009', stratum='serie_vs_base',
         source=fol('11152_SB', '11152', 'SERIE SERIE B', '12/03/2021', 'BBVA CONSUMO 11, FONDO DE TITULIZACION'),
         cand=cand_fol('11152'), label='AMBIGUOUS',
         notes='SERIE B de FTA 11152 vs base'),
    # control: serie vs FTA distinto -> NO_LINK
    dict(key='AMB-010', stratum='serie_vs_base',
         source=fol('11202_SA', '11202', 'SERIE Serie A', '23/09/2021', 'FONDO DE TITULIZACION SANTANDER'),
         cand=cand_fol('11240'), label='NO_LINK',
         notes='Serie de FTA 11202 vs FTA 11240: registros distintos'),
    # ---------- versionado CCFF: timing resoluble ----------
    dict(key='AMB-011', stratum='ccff_version_timing',
         source=ccff('CCFF_11357_009', '11357', '21/03/2025',
                     'XS3032821814', 'BANCO SANTANDER, S.A.'),
         cand=cand_fol('11357', version='base'), label='EXACT_LINK',
         rel='DEFINES_TERMS_FOR',
         notes='CCFF presentada 21/03/2025; suplemento 11357.2 es '
               '09/10/2025 (posterior): la base vigente es la correcta'),
    dict(key='AMB-012', stratum='ccff_version_timing',
         source=ccff('CCFF_11357_010', '11357', '09/05/2025',
                     'XS3071390226', 'BANCO SANTANDER, S.A.'),
         cand=cand_fol('11357', version='supplement.2'), label='NO_LINK',
         notes='el suplemento 11357.2 (09/10/2025) postdata la CCFF '
               '(presentada 09/05/2025); no puede definir sus terminos'),
    dict(key='AMB-013', stratum='ccff_version_timing',
         source=ccff('CCFF_11286_014', '11286', '10/07/2024',
                     'ES0305067K19', 'BBVA GLOBAL MARKETS B.V.'),
         cand=cand_fol('11286', version='base'), label='AMBIGUOUS',
         notes='CCFF presentada 10/07/2024, DESPUES de suplementos '
               '11286.1 (17/08/2023) y .4 (13/06/2024): no se puede '
               'saber desde la fila si los terminos salen del base o '
               'de la version suplementada'),
    dict(key='AMB-014', stratum='ccff_version_timing',
         source=ccff('CCFF_11286_014', '11286', '10/07/2024',
                     'ES0305067K19', 'BBVA GLOBAL MARKETS B.V.'),
         cand=cand_fol('11286', version='supplement.4'), label='AMBIGUOUS',
         notes='el suplemento .4 (13/06/2024) precede a la CCFF '
               '(10/07/2024): puede ser el documento vigente, o no; '
               'la fila no lo resuelve'),
    # ---------- admisiones hermanas mismo ISIN ----------
    dict(key='AMB-015', stratum='same_isin_sibling_admissions',
         source=adm('ADM_143165', 'MFE-MEDIAFOREUROPE N.V.',
                    'NL0015001OI1', '30/09/2025'),
         cand={'type': 'admission', 'record_key': 'ADM_143162',
               'isin': 'NL0015001OI1'}, label='AMBIGUOUS',
         notes='tres admisiones del mismo ISIN (143160/143162/143165): '
               'eventos distintos, relacion entre documentos no decidible'),
    # ---------- ISIN ausente: evidencia insuficiente ----------
    dict(key='AMB-016', stratum='insufficient_isin_evidence',
         source=adm('ADM_143193', 'ARTECHE LANTEGI ELKARTEA, S.A.', '',
                    '30/01/2026'),
         cand={'type': 'security', 'isin': 'ES0105449187'},
         label='AMBIGUOUS',
         notes='admision sin ISIN observable; no se puede confirmar '
               'ni descartar el instrumento'),
    dict(key='AMB-017', stratum='insufficient_isin_evidence',
         source=ccff('CCFF_11357_009', '11357', '21/03/2025',
                     'XS3032821814', 'BANCO SANTANDER, S.A.'),
         cand={'type': 'folleto'}, label='AMBIGUOUS',
         notes='candidato sin registro_oficial: no hay estructura '
               'que verificar'),
    # ---------- misma fuente, rol incompatible ----------
    dict(key='AMB-018', stratum='role_incompatible',
         source=fol('11221', '11221', 'DOC. REGISTRO', '24/03/2022', 'MONTEPINO LOGISTICA SOCIMI, S.A.'),
         cand={'type': 'security', 'isin': 'ES0105449187'},
         label='AMBIGUOUS',
         notes='doc de registro SOCIMI (equity) vs instrumento de deuda: '
               'rol incompatible, sin evidencia de relacion'),
]

# verificar que ningun record_key usado pertenece a scout/holdout
leaks = []
for c in CASES:
    rk = c['source']['record_key']
    if rk in used:
        leaks.append(rk)
    ck = (c['cand'] or {}).get('record_key')
    if ck and ck in used:
        leaks.append(ck)
assert not leaks, f'records ya usados: {leaks}'

out = {'manifest': 'linkage-ambiguity-dev',
       'purpose': 'dev set de ambiguedad real; etiquetado manual; '
                  'NO forma parte de scout ni holdout',
       'n_cases': len(CASES),
       'cases': [{'case_key': c['key'], 'stratum': c['stratum'],
                  'source': c['source'], 'candidate': c['cand'],
                  'label': c['label'],
                  'relation_if_exact': c.get('rel'),
                  'label_source': 'manual_dev',
                  'notes': c['notes']} for c in CASES]}
json.dump(out, open(OUT / 'cases.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('casos:', len(CASES))
from collections import Counter
print(Counter(c['label'] for c in CASES))
print(Counter(c['stratum'] for c in CASES))
