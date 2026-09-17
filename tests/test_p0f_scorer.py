"""P0-F scorer tests — synthetic fixtures only.

No real P0-D results or gold are read here; the scorer contract forbids
loading them during development.
"""
import pytest

from p0 import score_p0 as S


SCHEMA = {'fields': [
    {'id': 'isin', 'critical': True},
    {'id': 'issuer', 'critical': False},
    {'id': 'coupon_rate', 'critical': True},
    {'id': 'notes', 'critical': False},
]}
FAMILIES = {'isin': 'Identity', 'issuer': 'Identity',
            'coupon_rate': 'Coupon', 'notes': 'Other'}
STRATA = {'C1': 'LOW', 'C2': 'HIGH'}
MODE = {'C1': {'RA': 'MANUAL', 'RB': 'ASSISTED'},
        'C2': {'RA': 'ASSISTED', 'RB': 'MANUAL'}}


def gold(status, value=None):
    return {'fields': {'isin': {'gold_status': status, 'gold_value': value}}}


def dec(decision, value=None, pointers=None, origin='MANUAL_DISCOVERY'):
    return {'field': 'isin', 'decision': decision, 'value': value,
            'origin': origin, 'evidence_pointers': pointers or []}


# ---------- value equality ----------

def test_value_equal_normalizes():
    assert S.value_equal('ES0001 ', ' es0001')
    assert S.value_equal(3.5, '3,5')
    assert not S.value_equal('ES0001', 'ES0002')


def test_value_equal_multivalue_extra_wrong_not_exact():
    assert S.value_equal(['a', 'b'], ['B', 'A '])
    assert not S.value_equal(['a', 'b'], ['a', 'b', 'c'])
    assert not S.value_equal(['a'], ['a', 'b'])
    assert not S.value_equal('a', ['a'])


def test_value_equal_mechanical_equivalences():
    # dates ES/EN -> same date
    assert S.value_equal('17 de julio de 2020', '2020-07-17')
    assert S.value_equal('10 July 2020', '2020-07-10')
    # ISO-4217 names
    assert S.value_equal('Euros', 'EUR')
    assert S.value_equal('dólares', 'USD')
    # ES/EN number formats
    assert S.value_equal('1.750.000 euros', '1,750,000 EUR')
    assert S.value_equal('0,875%', '0.875%')
    # punctuation-insensitive enum codes
    assert S.value_equal('Act/Act (ICMA)', 'ACT_ACT_ICMA')
    # containment with consistent numeric content
    assert S.value_equal('4.35%', '4.35% of the initial nominal investment')
    # but NOT when numeric content differs (extra asserted quantity)
    assert not S.value_equal('75%', '75% of initial price (2,472.165 pts)')
    assert not S.value_equal('100%', '1100%')
    # no translation/synonymy: stays unequal, counts as residual
    assert not S.value_equal('anualmente', 'ANNUAL')
    assert not S.value_equal('fijo', '0,875% nominal anual')


def test_timing_status_from_events_frozen_rule():
    ev = [{'event_type': 'CASE_OPENED', 'ts': 100},
          {'event_type': 'CASE_PAUSED', 'ts': 200},
          {'event_type': 'CASE_RESUMED', 'ts': 400},
          {'event_type': 'CASE_SUBMITTED', 'ts': 500}]
    assert S.timing_status_from_events(ev, 500) == 'VALID'
    ev[2]['ts'] = 600   # pause of 400 s > 300
    ev[3]['ts'] = 900
    assert S.timing_status_from_events(ev, 900) == 'INVALID_TIMING'
    # paused and never resumed: gap to submission counts
    ev2 = [{'event_type': 'CASE_OPENED', 'ts': 100},
           {'event_type': 'CASE_PAUSED', 'ts': 200}]
    assert S.timing_status_from_events(ev2, 400) == 'VALID'
    assert S.timing_status_from_events(ev2, 900) == 'INVALID_TIMING'


# ---------- per-field classification ----------

@pytest.mark.parametrize('gold_status, gold_val, decision, expected', [
    ('CONFIRMED_VALUE', 'X', dec('CONFIRMED', 'X'), 'TP'),
    ('CONFIRMED_VALUE', 'X', dec('CONFIRMED', 'Y'), 'FP_WRONG_VALUE'),
    ('CONFIRMED_VALUE', 'X', dec('MISSING'), 'FN'),
    ('CONFIRMED_VALUE', 'X', dec('REJECTED'), 'FN'),
    ('CONFIRMED_VALUE', 'X', dec('CONFLICT'), 'FN'),
    ('CONFIRMED_VALUE', 'X', None, 'FN'),
    ('CONFLICT', None, dec('CONFLICT'), 'CONFLICT_OK'),
    ('CONFLICT', None, dec('CONFIRMED', 'X'), 'FP_CONFLICT_DENIED'),
    ('CONFLICT', None, dec('MISSING'), 'FN'),
    ('MISSING', None, dec('MISSING'), 'TN'),
    ('MISSING', None, dec('NOT_APPLICABLE'), 'TN'),
    ('MISSING', None, dec('CONFIRMED', 'X'), 'FP_INVENTED'),
    ('MISSING', None, dec('CONFLICT'), 'INCORRECT_STATUS'),
    ('MISSING', None, None, 'TN'),
    ('NOT_APPLICABLE', None, dec('NOT_APPLICABLE'), 'TN'),
    ('NOT_APPLICABLE', None, dec('CONFIRMED', 'X'), 'FP_INVENTED'),
])
def test_classify_unit(gold_status, gold_val, decision, expected):
    assert S.classify_unit(gold_status, gold_val, decision,
                           critical=True) == expected


def test_critical_error_only_on_critical_fields():
    assert S.is_critical_error('FP_WRONG_VALUE', critical=True)
    assert S.is_critical_error('FP_INVENTED', critical=True)
    assert S.is_critical_error('FP_CONFLICT_DENIED', critical=True)
    assert not S.is_critical_error('FP_WRONG_VALUE', critical=False)
    assert not S.is_critical_error('FN', critical=True)


# ---------- evidence / safety ----------

def _ok_validator(pointer, allowed):
    return ('OK', None) if pointer.get('doc_id') in allowed \
        else ('BROKEN_EVIDENCE', 'doc not authorized')


def test_unsupported_confirmed_and_critical_error():
    rows = S.score_review(
        [dec('CONFIRMED', 'WRONG',
             [{'doc_id': 'DOC', 'page': 1}])],
        gold('CONFIRMED_VALUE', 'RIGHT')['fields'], SCHEMA, {'DOC'},
        pointer_validator=_ok_validator)
    assert rows[0]['outcome'] == 'FP_WRONG_VALUE'
    assert rows[0]['critical_error']
    assert rows[0]['evidence_valid']

    rows = S.score_review(
        [dec('CONFIRMED', 'RIGHT',
             [{'doc_id': 'OUTSIDE', 'page': 1}])],
        gold('CONFIRMED_VALUE', 'RIGHT')['fields'], SCHEMA, {'DOC'},
        pointer_validator=_ok_validator)
    assert rows[0]['outcome'] == 'TP'
    assert rows[0]['unsupported_confirmed']
    assert not rows[0]['critical_error']

    rows = S.score_review(
        [dec('CONFIRMED', 'RIGHT', [])],
        gold('CONFIRMED_VALUE', 'RIGHT')['fields'], SCHEMA, {'DOC'},
        pointer_validator=_ok_validator)
    assert rows[0]['unsupported_confirmed']


# ---------- timing ----------

def _review(rid, cid, mode, secs, status='VALID', decisions=(), events=()):
    return {'reviewer_id': rid, 'case_id': cid, 'mode': mode,
            'active_seconds': secs, 'timing_status': status,
            'decisions': list(decisions), 'events': list(events)}


def test_paired_timing_and_bootstrap_determinism():
    reviews = [
        _review('RA', 'C1', 'MANUAL', 100), _review('RB', 'C1', 'ASSISTED', 40),
        _review('RB', 'C2', 'MANUAL', 200), _review('RA', 'C2', 'ASSISTED', 50)]
    t = S.timing_scores(reviews, MODE)
    assert t['n_valid_pairs'] == 2
    assert t['median_time_ratio'] == pytest.approx(0.325)
    assert t['n_assisted_faster'] == 2
    lo, hi = S.bootstrap_median_ci([0.4, 0.25])
    lo2, hi2 = S.bootstrap_median_ci([0.4, 0.25])
    assert (lo, hi) == (lo2, hi2)  # fixed seed -> deterministic


def test_invalid_timing_excluded_and_inconclusive():
    reviews = [_review('RA', 'C1', 'MANUAL', 100, 'INVALID_TIMING'),
               _review('RB', 'C1', 'ASSISTED', 40)]
    t = S.timing_scores(reviews, MODE)
    assert t['n_valid_pairs'] == 0
    gates = S.evaluate_gates(t, {'by_mode': {}}, {}, {})
    assert gates['TIME']['verdict'] == 'INCONCLUSIVE'
    verdict, _ = S.final_verdict(gates, freeze_ok=True)
    assert verdict == 'INCONCLUSIVE'


# ---------- gates / verdict ----------

def _full_rows(mode, outcomes):
    return [{'mode': mode, 'case_id': 'C', 'field': 'f', 'critical': False,
             'outcome': o, 'decision': 'CONFIRMED', 'evidence_valid': True,
             'unsupported_confirmed': False, 'critical_error': False}
            for o in outcomes]


def test_quality_gates_noninferiority():
    rows = (_full_rows('ASSISTED', ['TP'] * 99 + ['FP_INVENTED'])
            + _full_rows('MANUAL', ['TP'] * 90 + ['FN'] * 10))
    q = S.quality_scores(rows, {}, FAMILIES)
    assert q['by_mode']['ASSISTED']['precision'] == pytest.approx(0.99)
    t = {'n_valid_pairs': 30, 'median_time_ratio': 0.5,
         'n_assisted_faster': 25, 'bootstrap': {'ci95': [0.4, 0.7]}}
    gates = S.evaluate_gates(
        t, q, {'assisted_critical_errors': 0,
               'assisted_unsupported_confirmed': 0,
               'assisted_evidence_rate': 1.0},
        {'navigation_rate': 1.0, 'wrong_document_links': 0})
    assert all(g['verdict'] == 'PASS' for g in gates.values())
    verdict, _ = S.final_verdict(gates, freeze_ok=True)
    assert verdict == 'PASS'


def test_no_near_pass_single_failure_fails():
    t = {'n_valid_pairs': 30, 'median_time_ratio': 0.5,
         'n_assisted_faster': 25, 'bootstrap': {'ci95': [0.4, 0.7]}}
    q = {'by_mode': {'ASSISTED': {'precision': 1.0, 'recall': 1.0},
                     'MANUAL': {'precision': 0.9, 'recall': 0.9}}}
    gates = S.evaluate_gates(
        t, q, {'assisted_critical_errors': 1,
               'assisted_unsupported_confirmed': 0,
               'assisted_evidence_rate': 1.0},
        {'navigation_rate': 1.0, 'wrong_document_links': 0})
    assert gates['SAFETY']['verdict'] == 'FAIL'
    verdict, _ = S.final_verdict(gates, freeze_ok=True)
    assert verdict == 'FAIL'  # no PASS WITH CAVEATS


def test_freeze_failure_fails_verdict():
    t = {'n_valid_pairs': 30, 'median_time_ratio': 0.5,
         'n_assisted_faster': 25, 'bootstrap': {'ci95': [0.4, 0.7]}}
    q = {'by_mode': {'ASSISTED': {'precision': 1.0, 'recall': 1.0},
                     'MANUAL': {'precision': 0.9, 'recall': 0.9}}}
    gates = S.evaluate_gates(
        t, q, {'assisted_critical_errors': 0,
               'assisted_unsupported_confirmed': 0,
               'assisted_evidence_rate': 1.0},
        {'navigation_rate': 1.0, 'wrong_document_links': 0})
    verdict, _ = S.final_verdict(gates, freeze_ok=False)
    assert verdict == 'FAIL'


# ---------- evidence navigation ----------

def test_evidence_navigation_counting():
    ev = [{'event_type': 'EVIDENCE_JUMP', 'payload': {'doc_id': 'DOC'}},
          {'event_type': 'EVIDENCE_JUMP', 'payload': {'doc_id': 'WRONG'}},
          {'event_type': 'PDF_SEARCH', 'payload': {}}]
    reviews = [_review('RB', 'C1', 'ASSISTED', 40,
                       decisions=[dec('CONFIRMED', 'X',
                                      [{'doc_id': 'DOC', 'page': 1}])],
                       events=ev)]
    truth = {'C1': {'fields': {'isin': {'gold_status': 'CONFIRMED_VALUE',
                                        'gold_value': 'X'}}}}
    per_review, rows = S.score_all(
        reviews, truth, SCHEMA,
        {'C1': {'documents': ['DOC'], 'graph': {'nodes': []}}},
        {'C1': []}, FAMILIES, pointer_validator=_ok_validator)
    r = per_review[0]
    assert r['nav_used'] == 3          # 2 jumps + 1 decision pointer
    assert r['nav_ok'] == 2
    assert r['nav_wrongdoc'] == 1
    assert r['n_pdf_search'] == 1
    e = S.evidence_scores(per_review)
    assert e['navigation_rate'] == pytest.approx(2 / 3)
    assert e['wrong_document_links'] == 1
    gates = S.evaluate_gates(
        {'n_valid_pairs': 0}, {'by_mode': {}}, {}, e)
    assert gates['EVIDENCE']['verdict'] == 'FAIL'
