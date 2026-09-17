import hashlib
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from p0.app import evidence
from p0.app.store import ReviewStore, StoreError


def test_confirmed_candidate_requires_nonempty_evidence(tmp_path):
    store = ReviewStore(tmp_path)
    candidate = {'candidate_id': 'D:isin', 'field': 'isin', 'evidence': []}
    with pytest.raises(StoreError):
        store.record_decision('R', 'C', 'isin', 'CONFIRMED', value='X',
                              candidate_id='D:isin', case_candidates=[candidate])
    assert store.decisions_for('C', 'R') == []


@pytest.mark.parametrize('pointer', [None, [], 'bad', {},
                                   {'doc_id': '../outside', 'page': 1},
                                   {'doc_id': 'D', 'page': True},
                                   {'doc_id': 'D', 'page': 1, 'bbox': [0]}])
def test_malformed_pointer_is_broken(pointer):
    assert evidence.validate_pointer(pointer)[0] == 'BROKEN_EVIDENCE'


@pytest.fixture
def source(tmp_path, monkeypatch):
    from p0.app import cases
    pdf = tmp_path / 'D.pdf'
    pdf.write_bytes(b'fixture')
    monkeypatch.setattr(cases, 'pdf_path', lambda doc: pdf)
    monkeypatch.setattr(cases, 'doc_sha256', lambda doc: hashlib.sha256(b'fixture').hexdigest())
    monkeypatch.setattr(cases, 'ir_for', lambda doc: {'pages': [
        {'page_no': 1, 'width': 100, 'height': 100,
         'blocks': [{'text': 'A' * 90 + ' real ending'}]}]})
    return pdf


@pytest.mark.parametrize('change', [
    {'page': True}, {'page': 0}, {'page': 2}, {'page': 1.0},
    {'bbox': [0, 10, float('nan'), 0]}, {'bbox': [0, 0, 0, 0]},
    {'bbox': []}, {'excerpt': 123}, {'excerpt': 'A' * 90 + ' invented ending'},
    {'sha256': '0' * 64},
])
def test_evidence_validation(source, change):
    assert evidence.validate_pointer({'doc_id': 'D', 'page': 1, **change})[0] == 'BROKEN_EVIDENCE'


def test_evidence_authorization(source):
    pointer = {'doc_id': 'D', 'page': 1}
    assert evidence.validate_pointer(pointer, {'D'})[0] == 'OK'
    audit = evidence.audit_case('C', [pointer], {'OTHER'})
    assert audit['wrong_document_links'] == 1
    assert audit['ok'] == 0


def test_timing_restart_duplicate_open_and_submit(tmp_path):
    store = ReviewStore(tmp_path)
    store.record_event('R', 'C', 'CASE_OPENED', ts=0)
    store.record_event('R', 'C', 'CASE_OPENED', ts=5)
    other = ReviewStore(tmp_path)
    assert other.active_seconds('C', 'R', now=10) == 10
    other.record_event('R', 'C', 'CASE_PAUSED', ts=10)
    store.record_event('R', 'C', 'CASE_RESUMED', ts=400)
    review = other.submit_review('R', 'C', {'fields': []}, ts=410)
    assert review['active_seconds'] == 20
    assert review['timing_status'] == 'INVALID_TIMING'
    assert store.active_seconds('C', 'R', now=900) == 20
    assert store.submit_review('R', 'C', {'fields': []}, ts=500) == review
    assert len(store._read(store.reviews_path)) == 1
    with pytest.raises(StoreError, match='already submitted'):
        store.record_decision('R', 'C', 'isin', 'MISSING')


def test_concurrent_submit_is_single_commit(tmp_path):
    stores = [ReviewStore(tmp_path), ReviewStore(tmp_path)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda i: stores[i % 2].submit_review(
            'R', 'C', {'fields': []}), range(30)))
    assert all(r == results[0] for r in results)
    assert len(stores[0]._read(stores[0].reviews_path)) == 1
    assert len(stores[0]._read(tmp_path / 'closeouts.jsonl')) == 1


def test_submit_closeout_recovered_after_failure(tmp_path, monkeypatch):
    store = ReviewStore(tmp_path)
    append = store._append
    def fail_closeout(path, obj):
        if path.name == 'closeouts.jsonl':
            raise OSError('disk error')
        return append(path, obj)
    monkeypatch.setattr(store, '_append', fail_closeout)
    with pytest.raises(OSError):
        store.submit_review('R', 'C', {'fields': []}, ts=10)
    other = ReviewStore(tmp_path)
    review = other.submit_review('R', 'C', {'fields': []}, ts=20)
    assert review['submitted_at'] == 10
    assert other._read(tmp_path / 'closeouts.jsonl') == [review['closeout']]


def test_partial_log_fails_closed(tmp_path):
    path = tmp_path / 'decisions.jsonl'
    path.write_bytes(b'{"partial":')
    with pytest.raises(StoreError, match='corrupt log'):
        ReviewStore(tmp_path).record_decision('R', 'C', 'isin', 'MISSING')
    assert path.read_bytes() == b'{"partial":'


@pytest.mark.parametrize('kwargs', [
    {'field': 'unknown'}, {'origin': 'FIELD_STATUS', 'decision': 'CONFIRMED', 'value': 'X'},
    {'decision': 'REJECTED', 'candidate_id': 'unknown'},
    {'value': float('nan')}, {'evidence_pointers': {}},
])
def test_invalid_decisions_do_not_append(tmp_path, kwargs):
    store = ReviewStore(tmp_path)
    args = {'field': 'isin', 'decision': 'MISSING', **kwargs}
    with pytest.raises(StoreError):
        store.record_decision('R', 'C', **args)
    assert store.decisions_for('C', 'R') == []


def test_session_atomic_failure_preserves_original(tmp_path, monkeypatch):
    from p0.app import session
    monkeypatch.setattr(session, 'RUNTIME', tmp_path)
    path = session._write_session('R', [], 'test')
    before = path.read_bytes()
    def fail_replace(*args):
        raise OSError('disk error')
    monkeypatch.setattr(session.os, 'replace', fail_replace)
    with pytest.raises(OSError):
        session.save_session(path, session.load_session(path))
    assert path.read_bytes() == before
    assert not list(tmp_path.glob('*.tmp'))


def test_frontend_safety_and_failed_manual_save():
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node required for frontend regression')
    script = r'''
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const elements = new Map();
const element = () => ({textContent: '', innerHTML: '', value: '', className: '',
  style: {}, classList: {add() {}, remove() {}}, appendChild() {},
  querySelector() { return element(); }, addEventListener() {}});
const context = {console, URL, setTimeout, clearTimeout, setInterval, clearInterval,
  document: {getElementById(id) { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); },
    createElement: element, querySelectorAll() {return [];}, addEventListener() {}},
  window: {addEventListener() {}}, fetch: async () => {throw new Error('offline');}};
vm.createContext(context);
let src = fs.readFileSync(process.argv[1], 'utf8').replace(/init\(\);\s*$/, '');
vm.runInContext(src, context);
(async () => {
  assert.equal(vm.runInContext('safeUrl("javascript:alert(1)")', context), null);
  const html = vm.runInContext(`candRow({id:'isin'}, {value:'<img src=x onerror=bad>', evidence:[{excerpt:'<svg onload=bad>', doc_id:'<b>bad</b>', page:1}]}).innerHTML`, context);
  assert(!html.includes('<img') && !html.includes('<svg') && !html.includes('<b>bad'));
  await assert.rejects(vm.runInContext('api.get("/bad")', context));
  assert(elements.get('toast').textContent.includes('offline'));
  vm.runInContext(`S.caseId='C'; S.decisions={}; mmField='isin'; S.capturedEv={doc_id:'D',page:1}; $('mm-value').value='preserve me';`, context);
  await assert.rejects(vm.runInContext("$('mm-ok').onclick()", context));
  assert.equal(elements.get('mm-value').value, 'preserve me');
  assert.equal(vm.runInContext('Object.keys(S.decisions).length', context), 0);
})().catch(e => { console.error(e); process.exitCode=1; });
'''
    path = Path(__file__).resolve().parents[1] / 'p0/app/static/app.js'
    result = subprocess.run([node, '-e', script, str(path)], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
