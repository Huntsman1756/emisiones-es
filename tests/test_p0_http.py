import hashlib
import http.client
import io
import json
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pypdfium2
import pytest
from PIL import Image
from pypdf import PdfWriter

from p0.app import server


@contextmanager
def running(app):
    srv = server.ThreadingHTTPServer(('127.0.0.1', 0), server.make_handler(app))
    srv.daemon_threads = False
    thread = threading.Thread(target=lambda: srv.serve_forever(poll_interval=0.01))
    thread.start()
    try:
        yield srv.server_port
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)
        app.close()
        assert not thread.is_alive()


@pytest.fixture
def http_app(tmp_path, monkeypatch):
    pdf = tmp_path / 'synthetic.pdf'
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=300)
    with pdf.open('wb') as output:
        writer.write(output)
    writer.close()
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    ir = {'pages': [{'page_no': 1, 'width': 200, 'height': 300,
                     'blocks': [{'text': 'Offline synthetic evidence',
                                 'bbox': {'l': 1, 't': 20, 'r': 100, 'b': 1}}]}]}
    pointer = {'doc_id': 'DOC', 'page': 1, 'sha256': sha}
    candidate = {'candidate_id': 'DOC:isin', 'field': 'isin', 'value': 'ES0000000000',
                 'evidence': [pointer], 'state': 'CANDIDATE'}
    cases = {
        'A': {'documents': ['DOC'], 'candidates': [candidate],
              'graph': {'nodes': [{'id': 'GRAPH'}], 'edges': []}},
        'M': {'documents': ['MANUAL'], 'candidates': [candidate],
              'graph': {'nodes': [{'id': 'HIDDEN'}]}},
        'OUTSIDE': {'documents': ['SECRET'], 'candidates': []},
    }
    documents = {'DOC', 'GRAPH', 'MANUAL', 'HIDDEN', 'SECRET'}
    monkeypatch.setattr(server.cases_mod, 'all_cases', lambda: cases)
    monkeypatch.setattr(server.cases_mod, 'pdf_path',
                        lambda doc: pdf if doc in documents else None)
    monkeypatch.setattr(server.cases_mod, 'ir_path',
                        lambda doc: tmp_path / 'synthetic.ir.json' if doc in documents else None)
    monkeypatch.setattr(server.cases_mod, 'ir_for',
                        lambda doc: ir if doc in documents else None)
    monkeypatch.setattr(server.cases_mod, 'doc_sha256', lambda doc: sha)
    session_path = tmp_path / 'session.json'
    session_path.write_text(json.dumps({
        'session_id': 'synthetic', 'reviewer_id': 'REVIEWER',
        'items': [{'case_id': cid, 'mode': mode, 'status': 'PENDING'}
                  for cid, mode in [('A', 'ASSISTED'), ('M', 'MANUAL'),
                                    ('MISSING', 'MANUAL')]]}), encoding='utf-8')
    app = server.App(session_path)
    with running(app) as port:
        def request(path, method='GET', body=None, headers=None, raw=None):
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
            hdrs = {'Host': f'127.0.0.1:{port}'}
            if method == 'POST':
                hdrs.update({'Origin': f'http://127.0.0.1:{port}',
                             'Content-Type': 'application/json'})
            hdrs.update(headers or {})
            data = raw if raw is not None else (
                json.dumps(body).encode('utf-8') if body is not None else None)
            if data is not None and 'Content-Length' not in hdrs:
                hdrs['Content-Length'] = str(len(data))
            try:
                conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
                for key, value in hdrs.items():
                    if value is not None:
                        conn.putheader(key, value)
                conn.endheaders(data)
                response = conn.getresponse()
                payload = response.read()
                response_headers = dict(response.getheaders())
                if response_headers.get('Content-Type', '').startswith('application/json'):
                    payload = json.loads(payload)
                return response.status, response_headers, payload
            finally:
                conn.close()
        yield SimpleNamespace(app=app, request=request, port=port, pdf=pdf,
                              pointer=pointer, ir=ir, tmp_path=tmp_path)


def test_repo_root_and_schema():
    assert server.REPO == Path(__file__).resolve().parents[1]
    assert server.SCHEMA['fields']


def test_frontend_workflow(http_app):
    request = http_app.request
    status, headers, session = request('/api/session')
    assert status == 200
    assert session['reviewer_id'] == 'REVIEWER'
    assert headers['Cache-Control'] == 'no-store'
    assert headers['Cross-Origin-Resource-Policy'] == 'same-origin'
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert 'Access-Control-Allow-Origin' not in headers
    assert request('/api/schema')[2] == server.SCHEMA
    assisted = request('/api/case/A')[2]
    manual = request('/api/case/M')[2]
    assert assisted['candidates'][0]['schema_field'] == 'isin'
    assert 'graph' not in manual and 'candidates' not in manual
    assert manual['source_links'] == [{'doc_id': 'MANUAL', 'label': 'MANUAL'}]
    assert request('/api/event', 'POST', {'case_id': 'A', 'event_type': 'CASE_OPENED'})[0] == 200
    status, _, result = request('/api/decision', 'POST', {
        'case_id': 'A', 'field': 'isin', 'decision': 'CONFIRMED',
        'value': 'ES0000000000', 'candidate_id': 'DOC:isin',
        'origin': 'MACHINE_CANDIDATE', 'evidence_pointers': []})
    assert status == 200
    assert result['decision']['evidence_pointers'] == [http_app.pointer]
    assert request('/api/audit/A')[2]['ok'] == 1
    assert request('/api/event', 'POST', {'case_id': 'A', 'event_type': 'CASE_SUBMITTED'})[0] == 200
    status, _, result = request('/api/submit', 'POST', {'case_id': 'A', 'reviewer_notes': ['offline']})
    assert status == 200
    assert result['review']['n_decisions'] == 1
    assert result['review']['closeout']['broken_evidence'] == 0
    persisted = json.loads(http_app.app.session_path.read_text(encoding='utf-8'))
    assert persisted['items'][0]['status'] == 'DONE'
    assert not list(http_app.tmp_path.glob('*.tmp'))


@pytest.mark.parametrize('cid', ['OUTSIDE', 'MISSING', 'UNKNOWN'])
def test_case_authorization_all_routes(http_app, cid):
    for path in (f'/api/case/{cid}', f'/api/audit/{cid}'):
        assert http_app.request(path)[0] == 404
    for path in ('/api/event', '/api/decision', '/api/submit'):
        assert http_app.request(path, 'POST', {'case_id': cid})[0] == 404
    assert not http_app.app.store.events_path.exists()
    assert not http_app.app.store.decisions_path.exists()
    assert not http_app.app.store.reviews_path.exists()


@pytest.mark.parametrize('doc', ['SECRET', 'HIDDEN', 'UNKNOWN'])
@pytest.mark.parametrize('action', ['meta', 'file', 'search?q=Offline', 'page/1.png'])
def test_document_authorization(http_app, doc, action):
    assert http_app.request(f'/api/doc/{doc}/{action}')[0] == 404


def test_documents_search_and_render(http_app, monkeypatch):
    for doc in ('DOC', 'GRAPH', 'MANUAL'):
        assert http_app.request(f'/api/doc/{doc}/meta')[0] == 200
    assert http_app.request('/api/doc/DOC/file')[2] == http_app.pdf.read_bytes()
    assert http_app.request('/api/doc/DOC/search?q=offline')[2]['matches'][0]['page'] == 1
    assert http_app.request('/api/doc/DOC/search?q=absent')[2] == {'matches': []}
    status, headers, png = http_app.request('/api/doc/DOC/page/1.png')
    assert status == 200 and headers['Content-Type'] == 'image/png'
    with Image.open(io.BytesIO(png)) as image:
        assert image.size == (320, 480)
    assert http_app.request('/api/doc/DOC/page/2.png')[0] == 404
    monkeypatch.setattr(server.cases_mod, 'ir_for', lambda doc: None)
    meta = http_app.request('/api/doc/DOC/meta')[2]
    assert meta['source'] == 'pdfium'
    assert meta['pages'] == [{'page_no': 1, 'width': 200, 'height': 300}]


@pytest.mark.parametrize('headers', [
    {'Host': 'attacker.invalid'}, {'Host': '127.0.0.1:1'}, {'Host': None},
    {'Host': 'localhost.attacker.invalid'}, {'Host': '127.0.0.1:80@attacker.invalid'},
    {'Origin': 'null'}, {'Origin': 'https://attacker.invalid'},
    {'Sec-Fetch-Site': 'cross-site'}, {'Sec-Fetch-Site': 'same-site'},
])
def test_browser_isolation(http_app, headers):
    assert http_app.request('/api/session', headers=headers)[0] == 403
    assert http_app.request('/api/event', 'POST', {'case_id': 'A', 'event_type': 'CASE_OPENED'},
                            headers=headers)[0] == 403
    assert not http_app.app.store.events_path.exists()


def test_post_requires_origin_json_and_no_preflight(http_app):
    request = http_app.request
    assert request('/api/event', 'POST', {}, headers={'Origin': None})[0] == 403
    for ctype in ('text/plain', 'application/x-www-form-urlencoded', 'multipart/form-data', ''):
        assert request('/api/event', 'POST', {}, headers={'Content-Type': ctype})[0] == 415
    assert request('/api/event', 'OPTIONS')[0] == 405
    host = f'localhost:{http_app.port}'
    assert request('/api/event', 'POST', {'case_id': 'A', 'event_type': 'CASE_OPENED'},
                   headers={'Host': host, 'Origin': f'http://{host}'})[0] == 200


@pytest.mark.parametrize('raw', [b'', b'{', b'[]', b'null', b'1', b'"x"', b'\xff',
                               b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}',
                               b'{"x":"\\ud800"}',
                               b'{"case_id":"A","case_id":"M"}',
                               b'{"x":' + b'[' * 1100 + b'0' + b']' * 1100 + b'}'])
def test_invalid_json(http_app, raw):
    assert http_app.request('/api/event', 'POST', raw=raw)[0] == 400
    assert http_app.request('/api/session')[0] == 200


@pytest.mark.parametrize('headers, expected', [
    ({'Content-Length': None}, 411), ({'Content-Length': '-1'}, 400),
    ({'Content-Length': 'x'}, 400), ({'Content-Length': '65537'}, 413),
    ({'Transfer-Encoding': 'chunked'}, 400), ({'Content-Encoding': 'gzip'}, 415),
    ({'Expect': '100-continue'}, 417),
])
def test_request_framing(http_app, headers, expected):
    assert http_app.request('/api/event', 'POST', raw=b'{}', headers=headers)[0] == expected


@pytest.mark.parametrize('header', ['Host', 'Origin', 'Content-Length'])
def test_duplicate_headers(http_app, header):
    host = f'127.0.0.1:{http_app.port}'
    value = {'Host': host, 'Origin': f'http://{host}', 'Content-Length': '2'}[header]
    raw = (f'POST /api/event HTTP/1.1\r\nHost: {host}\r\nOrigin: http://{host}\r\n'
           f'Content-Type: application/json\r\nContent-Length: 2\r\n{header}: {value}\r\n\r\n{{}}')
    with socket.create_connection(('127.0.0.1', http_app.port), timeout=5) as sock:
        sock.sendall(raw.encode())
        response = http.client.HTTPResponse(sock)
        response.begin()
        assert response.status == 400
        response.read()


def test_short_and_stalled_body(http_app, monkeypatch):
    monkeypatch.setattr(server, 'REQUEST_TIMEOUT', 0.15)
    for incomplete, expected in ((True, 400), (False, 408)):
        with socket.create_connection(('127.0.0.1', http_app.port), timeout=5) as sock:
            host = f'127.0.0.1:{http_app.port}'
            sock.sendall((f'POST /api/event HTTP/1.1\r\nHost: {host}\r\n'
                          f'Origin: http://{host}\r\nContent-Type: application/json\r\n'
                          'Content-Length: 20\r\n\r\n{}').encode())
            if incomplete:
                sock.shutdown(socket.SHUT_WR)
            response = http.client.HTTPResponse(sock)
            response.begin()
            assert response.status == expected
            response.read()
    assert http_app.request('/api/session')[0] == 200


@pytest.mark.parametrize('body', [
    {}, {'case_id': []}, {'case_id': 'A', 'event_type': []},
    {'case_id': 'A', 'event_type': 'CASE_OPENED', 'payload': []},
    {'case_id': 'A', 'event_type': 'CASE_OPENED', 'payload': {'doc_id': 'SECRET'}},
    {'case_id': 'A', 'event_type': 'CASE_OPENED', 'payload': {'x': 'x' * 8193}},
    {'case_id': 'A', 'event_type': 'CASE_OPENED', 'payload': {'x': [0] * 257}},
])
def test_event_types_and_limits(http_app, body):
    assert http_app.request('/api/event', 'POST', body)[0] == 400
    assert not http_app.app.store.events_path.exists()


@pytest.mark.parametrize('changes', [
    {'field': []}, {'field': 'unknown'}, {'decision': {}}, {'origin': []},
    {'candidate_id': []}, {'candidate_id': 'unknown', 'decision': 'REJECTED'},
    {'evidence_pointers': {}}, {'evidence_pointers': [1]},
    {'evidence_pointers': [{'doc_id': 'SECRET', 'page': 1}]},
    {'evidence_pointers': [{'doc_id': 'DOC', 'page': True}]},
    {'evidence_pointers': [{'doc_id': 'DOC', 'page': 1, 'bbox': [1]}]},
    {'case_id': 'M'},
])
def test_decision_validation_and_mode(http_app, changes):
    body = {'case_id': 'A', 'field': 'isin', 'decision': 'CONFIRMED',
            'value': 'ES0000000000', 'candidate_id': 'DOC:isin'}
    body.update(changes)
    assert http_app.request('/api/decision', 'POST', body)[0] == 400
    assert not http_app.app.store.decisions_path.exists()


@pytest.mark.parametrize('notes', ['text', {}, [1]])
def test_submit_notes_type(http_app, notes):
    assert http_app.request('/api/submit', 'POST', {'case_id': 'A', 'reviewer_notes': notes})[0] == 400
    assert not http_app.app.store.reviews_path.exists()


@pytest.mark.parametrize('suffix', [
    'page/0.png', 'page/-1.png', 'page/a.png', 'page/10001.png',
    'page/1.png?scale=nan', 'page/1.png?scale=inf', 'page/1.png?scale=-1',
    'page/1.png?scale=0', 'page/1.png?scale=4.01', 'page/1.png?scale=0.24',
    'page/1.png?scale=oops', 'page/1.png?scale=1&scale=2',
    'search?q=' + 'x' * 513,
])
def test_render_and_query_limits(http_app, suffix):
    assert http_app.request('/api/doc/DOC/' + suffix)[0] == 400


@pytest.mark.parametrize('path', ['/api/doc/DOC/extra/meta', '/api/case/extra/A',
                                  '/api/doc/DOC/page/1.png/extra', '/api/doc/../file',
                                  '/static/../server.py', '/static/%2e%2e/server.py',
                                  '/static/app.js:secret', '/static/', '/static/server.py'])
def test_exact_routes_and_static_traversal(http_app, path):
    assert http_app.request(path)[0] == 404


def test_static_allowlist_and_symlink(http_app, monkeypatch):
    for path in ('/', '/index.html', '/static/app.js', '/static/style.css'):
        status, headers, body = http_app.request(path)
        assert status == 200 and body
        assert "script-src 'self'" in headers['Content-Security-Policy']
    static = http_app.tmp_path / 'static'
    static.mkdir()
    monkeypatch.setattr(server, 'STATIC', static)
    (static / 'app.js').mkdir()
    assert http_app.request('/static/app.js')[0] == 404
    try:
        (static / 'index.html').symlink_to(http_app.pdf)
    except OSError:
        pytest.skip('symlink creation unavailable')
    assert http_app.request('/')[0] == 404


def test_internal_error_and_atomic_session_recovery(http_app, monkeypatch):
    original = http_app.app.session_path.read_bytes()
    replace = server.os.replace
    def fail(*args):
        raise OSError('private filesystem details')
    monkeypatch.setattr(server.os, 'replace', fail)
    status, _, result = http_app.request('/api/submit', 'POST', {'case_id': 'A'})
    assert status == 500 and result['error'] == 'internal server error'
    assert http_app.app.session_path.read_bytes() == original
    assert http_app.app.session['items'][0]['status'] == 'PENDING'
    assert not list(http_app.tmp_path.glob('*.tmp'))
    monkeypatch.setattr(server.os, 'replace', replace)
    assert http_app.request('/api/submit', 'POST', {'case_id': 'A'})[0] == 200
    assert len(http_app.app.store._read(http_app.app.store.reviews_path)) == 1


def test_concurrent_http_writes(http_app):
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda i: http_app.request('/api/event', 'POST', {
            'case_id': 'A', 'event_type': 'UI_ERROR', 'payload': {'i': i}}), range(20)))
    assert all(result[0] == 200 for result in results)
    events = http_app.app.store._read(http_app.app.store.events_path)
    assert sorted(event['payload']['i'] for event in events) == list(range(20))


def test_pdfium_serialization_cleanup_and_pixel_budget(http_app, monkeypatch):
    state = {'active': 0, 'max_active': 0, 'closed': [], 'size': (200, 300), 'fail': False}
    class Bitmap:
        def to_pil(self):
            if state['fail']:
                raise RuntimeError('synthetic conversion failure')
            return Image.new('RGB', (2, 2))
        def close(self):
            state['closed'].append('bitmap')
    class Page:
        def get_size(self):
            return state['size']
        def render(self, scale):
            return Bitmap()
        def close(self):
            state['closed'].append('page')
    class Document:
        def __init__(self, path):
            state['active'] += 1
            state['max_active'] = max(state['max_active'], state['active'])
            time.sleep(0.01)
        def __len__(self):
            return 1
        def __getitem__(self, index):
            return Page()
        def close(self):
            state['active'] -= 1
            state['closed'].append('doc')
    monkeypatch.setattr(pypdfium2, 'PdfDocument', Document)
    monkeypatch.setattr(server.cases_mod, 'ir_for', lambda doc: None)
    other = server.App(http_app.app.session_path)
    with running(other) as other_port:
        def other_meta():
            conn = http.client.HTTPConnection('127.0.0.1', other_port, timeout=5)
            try:
                conn.request('GET', '/api/doc/DOC/meta')
                response = conn.getresponse()
                response.read()
                return response.status
            finally:
                conn.close()
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(other_meta) if i % 2 else pool.submit(
                lambda: http_app.request('/api/doc/DOC/page/1.png')[0]) for i in range(12)]
            assert all(f.result() == 200 for f in futures)
    assert state['max_active'] == 1 and state['active'] == 0
    assert state['closed'].count('page') == state['closed'].count('doc')
    http_app.app.close()
    state['fail'] = True
    assert http_app.request('/api/doc/DOC/page/1.png')[0] == 500
    assert state['closed'][-3:] == ['bitmap', 'page', 'doc']
    assert state['active'] == 0
    state['fail'] = False
    state['size'] = (10000, 10000)
    assert http_app.request('/api/doc/DOC/page/1.png')[0] == 400
    assert state['closed'][-2:] == ['page', 'doc']


def test_render_cache_bounded_and_invalidated(http_app, monkeypatch):
    monkeypatch.setattr(server, 'MAX_CACHE_BYTES', 3000)
    for scale in (0.25, 0.5, 1, 1.6, 2):
        assert http_app.request(f'/api/doc/DOC/page/1.png?scale={scale}')[0] == 200
        assert http_app.app._cache_bytes <= 3000
        assert http_app.app._cache_bytes == sum(map(len, http_app.app._pagecache.values()))
    http_app.pdf.write_bytes(b'not a PDF')
    assert http_app.request('/api/doc/DOC/page/1.png?scale=0.25')[0] == 500
    http_app.app.close()
    assert not http_app.app._pagecache and http_app.app._cache_bytes == 0
