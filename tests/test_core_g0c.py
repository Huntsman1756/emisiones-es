"""Tests G0-C: normalizadores, linker, evidencia, reconciliacion,
licensing guard. Fixtures sinteticos o derivados del scout; nunca del
holdout."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import pytest
from decimal import Decimal

from emissions_es.extraction.normalize import (norm_currency, norm_date,
                                               norm_money, norm_number,
                                               norm_percent)
from emissions_es.linking.linker import adjudicate
from emissions_es.linking.rules import (Candidate, KnowledgeBase,
                                        SourceRecord)
from emissions_es.model import (FactStatus, IdentifierType, LinkDecision,
                                QualifiedIdentifier,
                                ReconciliationStatus, TermObservation,
                                EvidencePointer)
from emissions_es.reconciliation import reconcile


# ---------- normalizadores ----------

def test_norm_number_es_en():
    assert norm_number('3,625') == Decimal('3.625')
    assert norm_number('3.625') == Decimal('3.625')
    assert norm_number('25,000,000') == Decimal('25000000')
    assert norm_number('1.234.567,89') == Decimal('1234567.89')
    assert norm_number('') is None
    assert norm_number('abc') is None


def test_norm_percent():
    assert norm_percent('5.90%') == Decimal('5.90')
    assert norm_percent('3,375%') == Decimal('3.375')
    assert norm_percent('2,07 por ciento') == Decimal('2.07')
    assert norm_percent('sin cupon') is None


def test_norm_date():
    assert norm_date('5 August 2036') == '2036-08-05'
    assert norm_date('05/08/2036') == '2036-08-05'
    assert norm_date('10 de septiembre de 2031') == '2031-09-10'
    assert norm_date('no date') is None


def test_norm_currency():
    assert norm_currency('U.S dollars ("USD")') == 'USD'
    assert norm_currency('EUR') == 'EUR'
    assert norm_currency("Renminbi- Offshore CNY ('CNH')") == 'CNH'
    assert norm_currency('euros') == 'EUR'


def test_norm_money():
    m = norm_money('USD 25,000,000')
    assert m['amount'] == '25000000' and m['currency'] == 'USD'
    m = norm_money('Nominal: 750.000.000 Euros')
    assert m['amount'] == '750000000' and m['currency'] == 'EUR'
    assert norm_money('sin importe') is None


# ---------- identificadores ----------

def test_qualified_identifier():
    i = QualifiedIdentifier(
        identifier_type=IdentifierType.CNMV_CCFF_ID,
        identifier_value='CCFF_11400_043', source='cnmv')
    assert i.identifier_type == IdentifierType.CNMV_CCFF_ID


def test_ccff_same_registration_distinct_records():
    """CCFF_11400_043/044/045 comparten registro 11400 pero son
    registros de presentacion distintos: el linker NO puede enlazar
    por prefijo."""
    kb = KnowledgeBase()
    for ccff in ('CCFF_11400_043', 'CCFF_11400_044', 'CCFF_11400_045'):
        src = SourceRecord(family='cnmv_ccff', record_key=ccff,
                           registro_oficial='11400', numfol_link=None)
        res = adjudicate(src, Candidate(type='folleto',
                                        registro_oficial='11400'), kb)
        # sin enlace NUMFOL explicito observable -> AMBIGUOUS, nunca EXACT
        assert res.decision == LinkDecision.AMBIGUOUS


# ---------- linker ----------

def test_linker_ccff_exact():
    kb = KnowledgeBase(folletos=[{'registro_oficial': '11400',
                                  'emisor': 'X', 'rol': 'PROGRAMA RENTA FIJA'}])
    src = SourceRecord(family='cnmv_ccff', record_key='CCFF_11400_043',
                       registro_oficial='11400', numfol_link='11400')
    r = adjudicate(src, Candidate(type='folleto', registro_oficial='11400'), kb)
    assert r.decision == LinkDecision.EXACT_LINK
    assert r.relation == 'DEFINES_TERMS_FOR'
    assert r.rule_id == 'CNMV_CCFF_EXPLICIT_NUMFOL'


def test_linker_negative_evidence_no_link():
    src = SourceRecord(family='cnmv_ccff', record_key='CCFF_11400_043',
                       registro_oficial='11400', numfol_link='11400')
    r = adjudicate(src, Candidate(type='folleto', registro_oficial='11437'))
    assert r.decision == LinkDecision.NO_LINK
    assert r.negative_evidence


def test_linker_supplement():
    src = SourceRecord(family='cnmv_folletos_emision',
                       record_key='FOL_11424.1', registro_oficial='11424',
                       version_suffix='.1', rol='SUPLEMENTO')
    r = adjudicate(src, Candidate(type='folleto', registro_oficial='11424'))
    assert r.decision == LinkDecision.EXACT_LINK
    assert r.relation == 'SUPPLEMENTS'


def test_linker_admission_isin():
    src = SourceRecord(family='cnmv_admision', record_key='ADM_1',
                       isin='ES0100000001')
    r = adjudicate(src, Candidate(type='security', isin='ES0100000001'))
    assert r.decision == LinkDecision.EXACT_LINK
    assert r.relation == 'ADMISSION_OF'
    r2 = adjudicate(src, Candidate(type='security', isin='ES0100000002'))
    assert r2.decision == LinkDecision.NO_LINK


def test_linker_ambiguous_never_forced():
    src = SourceRecord(family='cnmv_folletos_emision',
                       record_key='FOL_X', registro_oficial='99999',
                       rol='OTRO')
    r = adjudicate(src, Candidate(type='unknown'))
    assert r.decision in (LinkDecision.AMBIGUOUS, LinkDecision.NO_LINK)


# ---------- reconciliacion ----------

def _t(v, src='cnmv'):
    return TermObservation(field='maturity', value=v,
                           status=FactStatus.DERIVED,
                           evidence=[EvidencePointer(source=src,
                                                     source_record_key='k')])


def test_reconcile_agree():
    r = reconcile('maturity', 'XS1', [_t('2036-08-05'), _t('2036-08-05', 'firds')])
    assert r.status == ReconciliationStatus.AGREE


def test_reconcile_conflict_preserved():
    r = reconcile('maturity', 'XS1', [_t('2036-08-05'), _t('2036-08-06', 'firds')])
    assert r.status == ReconciliationStatus.CONFLICT
    assert len(r.observations) == 2  # ninguna fuente descartada


def test_reconcile_source_only_missing():
    r = reconcile('maturity', 'XS1', [_t('2036-08-05')])
    assert r.status == ReconciliationStatus.SOURCE_ONLY
    r = reconcile('maturity', 'XS1', [])
    assert r.status == ReconciliationStatus.MISSING


# ---------- evidencia ----------

def test_term_observation_evidence_required():
    o = _t('x')
    assert o.evidence and o.evidence[0].source == 'cnmv'


# ---------- licensing guard ----------

def test_no_forbidden_deps_in_package():
    """gmft_pymupdf/PyMuPDF/Marker/MinerU/rateslib no pueden entrar al core."""
    import re as _re
    root = Path(__file__).resolve().parents[1]
    banned = _re.compile(r'import\s+(fitz|pymupdf|gmft_pymupdf|marker|mineru|rateslib)'
                         r'|from\s+(fitz|pymupdf|gmft_pymupdf|marker|mineru|rateslib)')
    offenders = []
    for p in (root / 'src').rglob('*.py'):
        if banned.search(p.read_text(encoding='utf-8', errors='replace')):
            offenders.append(str(p))
    assert not offenders, offenders


def test_no_forbidden_deps_declared():
    txt = (Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text()
    for dep in ('pymupdf', 'fitz', 'gmft_pymupdf', 'marker', 'mineru', 'rateslib'):
        assert dep not in txt.lower()


# ---------- oracle de calendario ----------

def test_payment_schedule_oracle():
    from datetime import date
    from emissions_es.reconciliation.oracle import expected_schedule
    s, d = expected_schedule('5 August in each year',
                             date(2026, 8, 5), date(2036, 8, 5))
    assert s == 'VALID' and d['n_dates'] == 10
    s, _ = expected_schedule(None, date(2026, 1, 1), date(2030, 1, 1))
    assert s == 'UNVERIFIABLE'
    s, _ = expected_schedule('quarterly', date(2030, 1, 1), date(2026, 1, 1))
    assert s == 'INVALID'
