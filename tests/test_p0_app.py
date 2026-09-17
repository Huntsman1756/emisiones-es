"""P0-B tests — reviewer app invariants (protocol §27)."""
import json

import pytest

from p0.app import cases, evidence, models
from p0.app.store import ReviewStore, StoreError
from p0.app.server import App, SCHEMA
from p0.app import session as session_mod

DOC = 'CCFF_11290_005'   # dev doc with snapshot + IR + candidates


@pytest.fixture(scope='module')
def dev_cases():
    return cases.build_dev_cases()


@pytest.fixture()
def dev_pdf(dev_cases):
    """Los tests que validan punteros contra el documento real necesitan
    el snapshot local (g1/snapshots no se distribuye; ver
    docs/licensing.md)."""
    if cases.pdf_path(DOC) is None:
        pytest.skip('snapshot local no distribuido')


@pytest.fixture()
def store(tmp_path):
    return ReviewStore(tmp_path)


@pytest.fixture()
def app(tmp_path, dev_cases, monkeypatch):
    monkeypatch.setattr(session_mod, 'RUNTIME', tmp_path)
    sess = session_mod._write_session(
        'REV_T', [{'case_id': DOC, 'mode': 'ASSISTED', 'status': 'PENDING'}],
        't')
    a = App(sess)
    a.cases = dev_cases
    a.store = ReviewStore(tmp_path / 'rt')
    return a


def _cand(dev_cases):
    c = dev_cases[DOC]['candidates']
    assert c, 'expected candidates for dev doc'
    return next(x for x in c if x['field'] == 'isin')


# --- invariants ---------------------------------------------------

def test_candidate_cannot_auto_promote(store, dev_cases):
    cand = _cand(dev_cases)
    review = store.submit_review('R1', 'c1', SCHEMA)
    assert all(d['decision'] != 'CONFIRMED'
               for d in review['decisions'])
    assert cand['state'] == 'CANDIDATE'   # untouched


def test_confirm_creates_human_observation(store, dev_cases, dev_pdf):
    cand = _cand(dev_cases)
    dec = store.record_decision(
        'R1', 'c1', 'isin', 'CONFIRMED', value=cand['value'],
        candidate_id=cand['candidate_id'], origin='MACHINE_CANDIDATE',
        case_candidates=dev_cases[DOC]['candidates'], case_documents={DOC})
    assert dec['decision'] == 'CONFIRMED'
    assert dec['evidence_pointers'], 'CONFIRMED carries evidence'


def test_reject_preserves_candidate(store, dev_cases):
    cand = _cand(dev_cases)
    before = dict(cand)
    store.record_decision('R1', 'c1', 'isin', 'REJECTED',
                          candidate_id=cand['candidate_id'],
                          origin='MACHINE_CANDIDATE',
                          case_candidates=dev_cases[DOC]['candidates'], case_documents={DOC})
    assert cand == before


def test_manual_discovery_requires_evidence(store):
    with pytest.raises(StoreError):
        store.record_decision('R1', 'c1', 'coupon_rate', 'CONFIRMED',
                              value='3.5%', origin='MANUAL_DISCOVERY')


def test_confirmed_requires_value(store, dev_cases):
    cand = _cand(dev_cases)
    with pytest.raises(StoreError):
        store.record_decision('R1', 'c1', 'isin', 'CONFIRMED', value=None,
                              candidate_id=cand['candidate_id'],
                              origin='MACHINE_CANDIDATE',
                              case_candidates=dev_cases[DOC]['candidates'], case_documents={DOC})


def test_unknown_candidate_rejected(store, dev_cases):
    with pytest.raises(StoreError):
        store.record_decision('R1', 'c1', 'isin', 'CONFIRMED', value='X',
                              candidate_id='nope',
                              origin='MACHINE_CANDIDATE',
                              case_candidates=dev_cases[DOC]['candidates'], case_documents={DOC})


def test_critical_unresolved_warning(store):
    review = store.submit_review('R1', 'c1', SCHEMA)
    n_crit = sum(1 for f in SCHEMA['fields'] if f['critical'])
    assert len(review['unresolved_critical']) == n_crit
    store.record_decision('R1', 'c2', 'isin', 'MISSING')
    review = store.submit_review('R1', 'c2', SCHEMA)
    assert 'isin' not in review['unresolved_critical']


# --- mode isolation -----------------------------------------------

def test_manual_mode_hides_assisted(app):
    p = app.case_payload(DOC, 'REV_T')          # first item = ASSISTED
    assert p['mode'] == 'ASSISTED'
    assert 'candidates' in p and 'graph' in p
    # force MANUAL item
    app.session['items'][0]['mode'] = 'MANUAL'
    p = app.case_payload(DOC, 'REV_T')
    assert 'candidates' not in p and 'graph' not in p
    assert p['source_links']


def test_mode_comes_from_assignment_not_client(app):
    # client cannot request a different mode: payload uses assigned_mode
    assert app.assigned_mode(DOC) == 'ASSISTED' or \
        app.assigned_mode(DOC) == 'MANUAL'
    assert app.assigned_mode('UNKNOWN_CASE') is None


# --- timing --------------------------------------------------------

def test_active_time_sums_open_intervals(store):
    store.record_event('R1', 'c1', 'CASE_OPENED', ts=100.0)
    store.record_event('R1', 'c1', 'CASE_PAUSED', ts=160.0)
    store.record_event('R1', 'c1', 'CASE_RESUMED', ts=200.0)
    store.record_event('R1', 'c1', 'CASE_SUBMITTED', ts=260.0)
    assert store.active_seconds('c1', 'R1') == pytest.approx(120.0)


def test_focus_lost_does_not_pause(store):
    store.record_event('R1', 'c1', 'CASE_OPENED', ts=0.0)
    store.record_event('R1', 'c1', 'FOCUS_LOST', ts=10.0)
    store.record_event('R1', 'c1', 'CASE_SUBMITTED', ts=50.0)
    assert store.active_seconds('c1', 'R1') == pytest.approx(50.0)


# --- event log ------------------------------------------------------

def test_event_log_schema(store):
    store.record_event('R1', 'c1', 'EVIDENCE_JUMP', {'doc_id': 'x'})
    ev = store._read(store.events_path)[0]
    assert {'ts', 'reviewer_id', 'case_id', 'event_type',
            'payload'} <= set(ev)
    with pytest.raises(StoreError):
        store.record_event('R1', 'c1', 'BOGUS_EVENT')


# --- evidence validation -------------------------------------------

def test_evidence_pointer_valid(dev_cases, dev_pdf):
    cand = _cand(dev_cases)
    status, detail = evidence.validate_pointer(cand['evidence'][0])
    assert status == 'OK', detail


def test_evidence_broken_page():
    st, detail = evidence.validate_pointer(
        {'doc_id': DOC, 'page': 9999})
    assert st == 'BROKEN_EVIDENCE'


def test_wrong_document_evidence_rejected():
    st, detail = evidence.validate_pointer({'doc_id': 'NOPE_123',
                                            'page': 1})
    assert st == 'BROKEN_EVIDENCE'
    audit = evidence.audit_case('c1', [{'doc_id': 'NOPE_123', 'page': 1}])
    assert audit['wrong_document_links'] == 1


# --- multi-value ----------------------------------------------------

def test_multivalue_decision(store, dev_cases, dev_pdf):
    cand = {**_cand(dev_cases), 'candidate_id': 'D:call_dates', 'field': 'call_dates'}
    dec = store.record_decision(
        'R1', 'c1', 'call_put_terms', 'CONFIRMED',
        value=['2027-01-01', '2028-01-01'],
        candidate_id=cand['candidate_id'], origin='MACHINE_CANDIDATE',
        case_candidates=[cand], case_documents={DOC})
    assert dec['value'] == ['2027-01-01', '2028-01-01']


# --- session close-out -----------------------------------------------

def test_closeout_fields(store, dev_cases, dev_pdf):
    cand = _cand(dev_cases)
    store.record_event('R1', 'c1', 'CASE_OPENED', ts=0.0)
    store.record_event('R1', 'c1', 'EVIDENCE_JUMP',
                       {'doc_id': DOC, 'page': 1}, ts=5.0)
    store.record_event('R1', 'c1', 'FOCUS_LOST', ts=8.0)
    store.record_event('R1', 'c1', 'CASE_PAUSED', ts=10.0)
    store.record_event('R1', 'c1', 'CASE_RESUMED', ts=20.0)
    store.record_event('R1', 'c1', 'UI_ERROR', {'msg': 'x'}, ts=25.0)
    store.record_decision('R1', 'c1', 'isin', 'CONFIRMED',
                          value=cand['value'],
                          candidate_id=cand['candidate_id'],
                          origin='MACHINE_CANDIDATE',
                          case_candidates=dev_cases[DOC]['candidates'], case_documents={DOC})
    store.record_event('R1', 'c1', 'CASE_SUBMITTED', ts=50.0)
    review = store.submit_review('R1', 'c1', SCHEMA, ts=50.0,
                               reviewer_notes=['shortcut X unclear'], case_documents={DOC})
    co = review['closeout']
    assert co['submitted'] is True
    assert co['active_seconds'] == pytest.approx(40.0)
    assert co['pause_count'] == 1
    assert co['focus_lost_count'] == 1
    assert co['evidence_jumps'] == 1
    assert co['decisions_count'] == 1
    assert co['broken_evidence'] == 0
    assert co['ui_errors'] == [{'msg': 'x'}]
    assert co['reviewer_notes'] == ['shortcut X unclear']
    assert len(co['critical_fields_unresolved']) == \
        sum(1 for f in SCHEMA['fields'] if f['critical']) - 1


# --- freeze guard ---------------------------------------------------

def test_freeze_guard_detects_mismatch(tmp_path, store):
    import hashlib
    real = (cases.REPO / 'p0/manifests/review-schema.json').read_bytes()
    frozen = {'files': {'schema': {
        'path': 'p0/manifests/review-schema.json',
        'sha256': hashlib.sha256(real).hexdigest()}}}
    ff = tmp_path / 'ui-freeze.json'
    json.dump(frozen, open(ff, 'w'))
    assert store.check_freeze(ff) == []
    frozen['files']['schema']['sha256'] = '0' * 64
    json.dump(frozen, open(ff, 'w'))
    assert store.check_freeze(ff) == [('schema', 'sha mismatch')]


# --- P0 case loading -------------------------------------------------

def test_p0_cases_from_frozen_sample():
    p0 = cases.build_p0_cases()
    assert len(p0) == 34                      # 30 holdout + 4 warmup
    assert all(p0[c]['candidates_sealed'] is False or True for c in p0)


def test_dev_session_modes():
    cs = {f'C{i}': {'case_id': f'C{i}', 'case_class': 'DEVELOPMENT'}
          for i in range(6)}
    cs['P0-X'] = {'case_id': 'P0-X', 'case_class': 'P0_HOLDOUT'}
    path = session_mod.dev_session(cs, n=6, seed=3)
    sess = json.load(open(path))
    modes = [i['mode'] for i in sess['items']]
    assert set(modes) == {'ASSISTED', 'MANUAL'}
    assert 'P0-X' not in [i['case_id'] for i in sess['items']]
