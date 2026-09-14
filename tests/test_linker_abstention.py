"""G0-C.1: abstencion real sobre ambiguedad (linkage-ambiguity-dev).

Cubre las familias del dev-set: sucesion no declarada, serie vs base,
CCFF vs versiones, ISIN insuficiente, admisiones hermanas, roles
incompatibles. Objetivo: 0 enlaces forzados sobre AMBIGUOUS reales.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from emissions_es.linking.linker import adjudicate
from emissions_es.linking.rules import (Candidate, KnowledgeBase,
                                        SourceRecord)
from emissions_es.model import LinkDecision

KB = KnowledgeBase(
    folletos=[
        {'registro_oficial': '11199', 'version_suffix': None,
         'rol': 'PROGRAMA RENTA FIJA', 'fecha_registro': '05/08/2021',
         'emisor': 'BANCA MARCH, S.A.'},
        {'registro_oficial': '11268', 'version_suffix': None,
         'rol': 'PROGRAMA RENTA FIJA', 'fecha_registro': '10/04/2023',
         'emisor': 'BANCA MARCH, S.A.'},
        {'registro_oficial': '11286', 'version_suffix': None,
         'rol': 'PROGRAMA RENTA FIJA', 'fecha_registro': '13/07/2023',
         'emisor': 'BBVA GLOBAL MARKETS B.V.'},
        {'registro_oficial': '11286', 'version_suffix': '.1',
         'rol': 'SUPLEMENTO', 'fecha_registro': '17/08/2023',
         'emisor': 'BBVA GLOBAL MARKETS B.V.'},
        {'registro_oficial': '11286', 'version_suffix': '.4',
         'rol': 'SUPLEMENTO', 'fecha_registro': '13/06/2024',
         'emisor': 'BBVA GLOBAL MARKETS B.V.'},
        {'registro_oficial': '11357', 'version_suffix': None,
         'rol': 'PROGRAMA RENTA FIJA', 'fecha_registro': '23/12/2024',
         'emisor': 'BANCO SANTANDER, S.A.'},
        {'registro_oficial': '11357', 'version_suffix': '.2',
         'rol': 'SUPLEMENTO', 'fecha_registro': '09/10/2025',
         'emisor': 'BANCO SANTANDER, S.A.'},
        {'registro_oficial': '11202', 'version_suffix': None,
         'rol': 'FOLLETO FTA', 'fecha_registro': '23/09/2021',
         'emisor': 'FONDO DE TITULIZACION SANTANDER'},
    ],
    admisiones=[
        {'record_key': 'ADM_143160', 'isin': 'ES0105449187',
         'emisor': 'MFE'},
        {'record_key': 'ADM_143162', 'isin': 'ES0105449187',
         'emisor': 'MFE'},
    ])


def test_succession_unverified_is_ambiguous_not_replaces():
    """Mismo emisor+rol, registro posterior: la fila no declara sucesion.
    La precedencia temporal no prueba REPLACES."""
    src = SourceRecord(family='cnmv_folletos_emision', record_key='FOL_11268',
                       registro_oficial='11268', rol='PROGRAMA RENTA FIJA',
                       emisor='BANCA MARCH, S.A.', fecha='10/04/2023')
    r = adjudicate(src, Candidate(type='folleto', registro_oficial='11199'), KB)
    assert r.decision == LinkDecision.AMBIGUOUS
    assert r.relation != 'REPLACES'
    assert r.negative_evidence


def test_succession_different_issuer_no_link():
    src = SourceRecord(family='cnmv_folletos_emision', record_key='FOL_11268',
                       registro_oficial='11268', rol='PROGRAMA RENTA FIJA',
                       emisor='BANCA MARCH, S.A.')
    r = adjudicate(src, Candidate(type='folleto', registro_oficial='11357'), KB)
    assert r.decision == LinkDecision.NO_LINK


def test_succession_candidate_not_in_corpus_ambiguous():
    src = SourceRecord(family='cnmv_folletos_emision', record_key='FOL_11268',
                       registro_oficial='11268', rol='PROGRAMA RENTA FIJA',
                       emisor='BANCA MARCH, S.A.')
    r = adjudicate(src, Candidate(type='folleto', registro_oficial='99998'), KB)
    assert r.decision == LinkDecision.AMBIGUOUS


def test_ccff_vs_supplement_postdating_is_no_link():
    """Suplemento posterior a la presentacion de la CCFF: no puede
    definir sus terminos."""
    src = SourceRecord(family='cnmv_ccff', record_key='CCFF_11357_010',
                       registro_oficial='11357', numfol_link='11357',
                       fecha='09/05/2025', isin='XS3071390226')
    r = adjudicate(src, Candidate(type='folleto', registro_oficial='11357',
                                  version='supplement.2'), KB)
    assert r.decision == LinkDecision.NO_LINK


def test_ccff_vs_supplement_predating_is_ambiguous():
    """Suplemento anterior a la CCFF: puede ser el vigente o no; la fila
    no lo resuelve."""
    src = SourceRecord(family='cnmv_ccff', record_key='CCFF_11286_014',
                       registro_oficial='11286', numfol_link='11286',
                       fecha='10/07/2024', isin='ES0305067K19')
    r = adjudicate(src, Candidate(type='folleto', registro_oficial='11286',
                                  version='supplement.4'), KB)
    assert r.decision == LinkDecision.AMBIGUOUS


def test_ccff_base_candidate_with_earlier_supplements_ambiguous():
    """Base + suplementos ya registrados a fecha de la CCFF: la version
    vigente no se resuelve desde la fila."""
    src = SourceRecord(family='cnmv_ccff', record_key='CCFF_11286_014',
                       registro_oficial='11286', numfol_link='11286',
                       fecha='10/07/2024', isin='ES0305067K19')
    r = adjudicate(src, Candidate(type='folleto', registro_oficial='11286',
                                  version='base'), KB)
    assert r.decision == LinkDecision.AMBIGUOUS


def test_ccff_base_candidate_no_earlier_supplements_exact():
    """CCFF anterior a cualquier suplemento: el base vigente es exacto."""
    src = SourceRecord(family='cnmv_ccff', record_key='CCFF_11357_009',
                       registro_oficial='11357', numfol_link='11357',
                       fecha='21/03/2025', isin='XS3032821814')
    r = adjudicate(src, Candidate(type='folleto', registro_oficial='11357',
                                  version='base'), KB)
    assert r.decision == LinkDecision.EXACT_LINK


def test_serie_same_register_no_doc_ambiguous():
    src = SourceRecord(family='cnmv_folletos_emision',
                       record_key='FOL_11202_SA', registro_oficial='11202',
                       rol='SERIE Serie A', doc_url=None)
    r = adjudicate(src, Candidate(type='folleto', registro_oficial='11202'), KB)
    assert r.decision == LinkDecision.AMBIGUOUS


def test_serie_different_register_no_link():
    src = SourceRecord(family='cnmv_folletos_emision',
                       record_key='FOL_11202_SA', registro_oficial='11202',
                       rol='SERIE Serie A', doc_url=None)
    r = adjudicate(src, Candidate(type='folleto', registro_oficial='11240'), KB)
    assert r.decision == LinkDecision.NO_LINK


def test_serie_with_own_doc_exact():
    src = SourceRecord(family='cnmv_folletos_emision',
                       record_key='FOL_11202_SA', registro_oficial='11202',
                       rol='SERIE Serie A',
                       doc_url='https://www.cnmv.es/x')
    r = adjudicate(src, Candidate(type='folleto', registro_oficial='11202'), KB)
    assert r.decision == LinkDecision.EXACT_LINK


def test_admission_missing_isin_ambiguous():
    src = SourceRecord(family='cnmv_admision', record_key='ADM_X', isin=None)
    r = adjudicate(src, Candidate(type='security', isin='ES0105449187'), KB)
    assert r.decision == LinkDecision.AMBIGUOUS


def test_admission_doc_candidate_never_exact():
    """El ISIN de admision identifica el instrumento, no el documento."""
    src = SourceRecord(family='cnmv_admision', record_key='ADM_143160',
                       isin='ES0105449187')
    r = adjudicate(src, Candidate(type='admission',
                                  record_key='ADM_143162'), KB)
    assert r.decision == LinkDecision.AMBIGUOUS
    assert any('admisiones comparten ISIN' in e
               for e in r.negative_evidence)


def test_ambiguity_dev_manifest_zero_forced_links():
    """End-to-end sobre g0/linkage-ambiguity-dev: 0 EXACT sobre gold
    AMBIGUOUS."""
    root = Path(__file__).resolve().parents[1]
    man = json.load(open(root / 'g0/linkage-ambiguity-dev/cases.json',
                         encoding='utf-8'))
    obs = json.load(open(root / '.work/observations.json',
                         encoding='utf-8'))
    kb = KnowledgeBase(folletos=obs['folletos'], ccff=obs['ccff'],
                       admisiones=obs['admisiones'])
    by_key = {o['source_record_key']: o
              for o in obs['folletos'] + obs['ccff'] + obs['admisiones']}
    forced = 0
    for case in man['cases']:
        s, o = case['source'], by_key.get(case['source']['record_key'], {})
        src = SourceRecord(
            family=s['family'], record_key=s['record_key'],
            registro_oficial=s.get('registro_oficial') or
            o.get('registro_oficial'),
            version_suffix=s.get('version_suffix') or
            o.get('version_suffix'),
            rol=s.get('rol') or o.get('rol'),
            isin=s.get('isin') or o.get('isin'),
            doc_url=s.get('doc_url') or o.get('doc_url'),
            numfol_link=s.get('numfol_link') or o.get('numfol_link'),
            emisor=s.get('emisor') or o.get('emisor'),
            fecha=s.get('fecha') or o.get('fecha'))
        c = case['candidate']
        res = adjudicate(src, Candidate(
            type=c.get('type', 'unknown'),
            registro_oficial=c.get('registro_oficial'),
            isin=c.get('isin'), doc_url=c.get('doc_url'),
            record_key=c.get('record_key'), rol=c.get('rol'),
            version=c.get('version')), kb)
        if case['label'] == 'AMBIGUOUS' and \
                res.decision == LinkDecision.EXACT_LINK:
            forced += 1
    assert forced == 0
