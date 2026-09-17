"""P0 reviewer app — stdlib HTTP server.

  python -m p0.app.server --session p0/runtime/session_dev_xxx.json \
      --port 8765

Mode is enforced server-side from the session item; the client cannot
switch a case between MANUAL and ASSISTED.
"""
import io
import json
import logging
import math
import os
import re
import sys
import tempfile
import threading
from collections import OrderedDict
from contextlib import ExitStack, closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from . import cases as cases_mod
from . import evidence as ev_mod
from . import models
from .store import ReviewStore, StoreError

REPO = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / 'static'
with (REPO / 'p0' / 'manifests' / 'review-schema.json').open(
        encoding='utf-8') as schema_file:
    SCHEMA = json.load(schema_file)

MAX_BODY = 65536
MAX_TARGET = 4096
MAX_TEXT = 8192
MAX_QUERY = 512
MAX_PAGE = 10000
MIN_SCALE = 0.25
MAX_SCALE = 4.0
MAX_PIXELS = 16000000
MAX_DIMENSION = 8192
MAX_CACHE_BYTES = 32 * 1024 * 1024
REQUEST_TIMEOUT = 10
IDENTIFIER = r'[A-Za-z0-9_-][A-Za-z0-9_.-]{0,127}'
PDFIUM_LOCK = threading.RLock()
LOGGER = logging.getLogger(__name__)


class HTTPError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _string(value, name, limit=128, optional=False):
    if optional and value is None:
        return
    if not isinstance(value, str) or not 1 <= len(value) <= limit:
        raise HTTPError(400, f'invalid {name}')


def _identifier(value):
    return isinstance(value, str) and re.fullmatch(IDENTIFIER, value) is not None


def _json_limits(value, depth=0):
    if depth > 16:
        raise HTTPError(400, 'JSON nesting too deep')
    if isinstance(value, str):
        if len(value) > MAX_TEXT:
            raise HTTPError(400, 'text too long')
        try:
            value.encode('utf-8')
        except UnicodeError:
            raise HTTPError(400, 'invalid Unicode text') from None
    if isinstance(value, float) and not math.isfinite(value):
        raise HTTPError(400, 'non-finite number')
    if isinstance(value, (dict, list)):
        if len(value) > 256:
            raise HTTPError(400, 'too many JSON entries')
        if isinstance(value, dict):
            for key in value:
                _json_limits(key, depth + 1)
            value = value.values()
        for item in value:
            _json_limits(item, depth + 1)


def _json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError('non-finite number')


class App:
    def __init__(self, session_path):
        self.session_path = Path(session_path).resolve()
        with self.session_path.open(encoding='utf-8') as session_file:
            self.session = json.load(session_file)
        if not isinstance(self.session, dict):
            raise ValueError('invalid session')
        if not _identifier(self.session.get('session_id')):
            raise ValueError('invalid session_id')
        _string(self.session.get('reviewer_id'), 'reviewer_id')
        items = self.session.get('items')
        if not isinstance(items, list) or any(
                not isinstance(it, dict) or not _identifier(it.get('case_id'))
                or it.get('mode') not in ('MANUAL', 'ASSISTED')
                for it in items):
            raise ValueError('invalid session items')
        self.cases = cases_mod.all_cases()
        self.store = ReviewStore(self.session_path.parent
                                 / self.session['session_id'])
        self.lock = threading.RLock()
        self._pagecache = OrderedDict()
        self._cache_bytes = 0

    def close(self):
        with self.lock:
            self._pagecache.clear()
            self._cache_bytes = 0

    def authorized_case(self, case_id):
        return (_identifier(case_id) and case_id in self.cases
                and self.assigned_mode(case_id) is not None)

    def case_documents(self, case_id):
        if not self.authorized_case(case_id):
            return set()
        case = self.cases[case_id]
        docs = set(case.get('documents', []))
        if self.assigned_mode(case_id) == 'ASSISTED':
            docs.update(n.get('id') for n in
                        (case.get('graph') or {}).get('nodes', []))
            docs.update(p.get('doc_id') for c in case.get('candidates', [])
                        for p in c.get('evidence', []))
        return {doc for doc in docs if _identifier(doc)}

    def authorized_doc(self, doc_id):
        return _identifier(doc_id) and any(
            doc_id in self.case_documents(it['case_id'])
            for it in self.session['items'])

    def save_completed(self, case_id):
        session = {**self.session, 'items': [
            {**it, 'status': 'DONE'} if it['case_id'] == case_id else dict(it)
            for it in self.session['items']]}
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode='w', encoding='utf-8', dir=self.session_path.parent,
                    prefix=self.session_path.name + '.', suffix='.tmp',
                    delete=False) as session_file:
                temporary = Path(session_file.name)
                json.dump(session, session_file, ensure_ascii=False, indent=1)
                session_file.flush()
                os.fsync(session_file.fileno())
            os.replace(temporary, self.session_path)
            self.session = session
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def assigned_mode(self, case_id):
        for it in self.session['items']:
            if it['case_id'] == case_id:
                return it['mode']
        return None

    def case_payload(self, case_id, reviewer_id):
        mode = self.assigned_mode(case_id)
        case = self.cases.get(case_id)
        if mode is None or case is None:
            return None
        payload = {
            'case_id': case_id, 'mode': mode,
            'isin': case.get('isin'), 'issuer': case.get('issuer'),
            'instrument_class': case.get('instrument_class'),
            'document_role': case.get('document_role'),
            'stratum': case.get('stratum'),
            'schema': SCHEMA,
            'field_families': models.FIELD_FAMILIES,
            'decisions': self.store.decisions_for(case_id, reviewer_id),
            'documents': [
                {'doc_id': d,
                 'pdf': f'/api/doc/{d}/page/1.png',
                 'has_ir': cases_mod.ir_path(d) is not None}
                for d in case.get('documents', [])],
        }
        if mode == 'ASSISTED':
            payload['graph'] = case.get('graph')
            payload['candidates'] = self._schema_candidates(case)
            payload['graph_diags'] = {
                k: case['graph'].get(k) for k in
                ('graph_nodes_found', 'graph_edges_found',
                 'review_required_edges', 'missing_expected_documents')
            } if case.get('graph') else None
        else:
            # MANUAL: source links only — no graph, no candidates
            payload['source_links'] = [
                {'doc_id': d, 'label': d} for d in
                case.get('documents', [])]
            if case.get('document_url'):
                payload['source_links'].append(
                    {'doc_id': 'CNMV', 'label': 'CNMV record',
                     'url': case['document_url']})
        return payload

    @staticmethod
    def _schema_candidates(case):
        """Map extractor candidates onto schema field ids. An ambiguous
        extractor field (e.g. barrier) may appear under several schema
        fields — the reviewer decides which it supports."""
        out = []
        for sid, efields in models.SCHEMA_TO_EXTRACTOR.items():
            for c in case.get('candidates', []):
                if c['field'] in efields:
                    oc = dict(c)
                    oc['schema_field'] = sid
                    out.append(oc)
        return out

    def render_page(self, doc_id, page_no, scale=1.6):
        if not self.authorized_doc(doc_id):
            return None
        if type(page_no) is not int or not 1 <= page_no <= MAX_PAGE:
            raise HTTPError(400, 'invalid page')
        if type(scale) not in (int, float) or not MIN_SCALE <= scale <= MAX_SCALE:
            raise HTTPError(400, 'invalid scale')
        pdf_path = cases_mod.pdf_path(doc_id)
        if pdf_path is None:
            return None
        stat = pdf_path.stat()
        cache_key = (str(pdf_path.resolve()), stat.st_mtime_ns, stat.st_size,
                     page_no, float(scale))
        with self.lock, PDFIUM_LOCK:
            cached = self._pagecache.get(cache_key)
            if cached is not None:
                self._pagecache.move_to_end(cache_key)
                return cached
            import pypdfium2 as pdfium
            with ExitStack() as stack:
                doc = stack.enter_context(closing(pdfium.PdfDocument(str(pdf_path))))
                if page_no > len(doc):
                    return None
                page = stack.enter_context(closing(doc[page_no - 1]))
                width, height = page.get_size()
                if any(not math.isfinite(n) or n <= 0 for n in (width, height)):
                    raise HTTPError(422, 'invalid page dimensions')
                width, height = math.ceil(width * scale), math.ceil(height * scale)
                if max(width, height) > MAX_DIMENSION or width * height > MAX_PIXELS:
                    raise HTTPError(400, 'render exceeds pixel limit')
                bitmap = stack.enter_context(closing(page.render(scale=scale)))
                image = stack.enter_context(closing(bitmap.to_pil()))
                buffer = stack.enter_context(io.BytesIO())
                image.save(buffer, 'PNG')
                data = buffer.getvalue()
            if len(data) <= MAX_CACHE_BYTES:
                while self._pagecache and self._cache_bytes + len(data) > MAX_CACHE_BYTES:
                    _, removed = self._pagecache.popitem(last=False)
                    self._cache_bytes -= len(removed)
                self._pagecache[cache_key] = data
                self._cache_bytes += len(data)
            return data

    def doc_meta(self, doc_id):
        if not self.authorized_doc(doc_id):
            return None
        ir = cases_mod.ir_for(doc_id)
        pdf = cases_mod.pdf_path(doc_id)
        if pdf is None:
            return None
        meta = {'doc_id': doc_id, 'sha256': cases_mod.doc_sha256(doc_id)}
        if ir:
            meta['pages'] = [{'page_no': p['page_no'], 'width': p['width'],
                              'height': p['height']} for p in ir['pages']]
            meta['source'] = 'ir'
        else:
            import pypdfium2 as pdfium
            with PDFIUM_LOCK, closing(pdfium.PdfDocument(str(pdf))) as doc:
                if len(doc) > MAX_PAGE:
                    raise HTTPError(422, 'document has too many pages')
                meta['pages'] = []
                for i in range(len(doc)):
                    with closing(doc[i]) as page:
                        width, height = page.get_size()
                        meta['pages'].append({'page_no': i + 1,
                                              'width': width, 'height': height})
            meta['source'] = 'pdfium'
        return meta

    def search_doc(self, doc_id, query):
        ir = cases_mod.ir_for(doc_id)
        if not ir or not query:
            return {'matches': []}
        q = query.lower()
        matches = []
        for p in ir['pages']:
            for bl in p['blocks']:
                text = bl.get('text') or ''
                if q in text.lower():
                    matches.append({
                        'page': p['page_no'], 'bbox': [
                            bl['bbox']['l'], bl['bbox']['t'],
                            bl['bbox']['r'], bl['bbox']['b']],
                        'excerpt': text[:160]})
                    if len(matches) >= 100:
                        return {'matches': matches}
        return {'matches': matches}


def make_handler(app):
    class H(BaseHTTPRequestHandler):
        server_version = 'P0'
        sys_version = ''

        def setup(self):
            self.request.settimeout(REQUEST_TIMEOUT)
            super().setup()
            self._responded = False

        def log_message(self, *a):
            pass

        def end_headers(self):
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy',
                             "default-src 'self'; script-src 'self'; "
                             "style-src 'self' 'unsafe-inline'; "
                             "object-src 'none'; base-uri 'none'; "
                             "frame-ancestors 'none'; form-action 'none'")
            self.send_header('Connection', 'close')
            self.close_connection = True
            self._responded = True
            super().end_headers()

        def _send(self, body, ctype, code=200):
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            body = json.dumps(obj, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self._send(body, 'application/json; charset=utf-8', code)

        def send_error(self, code, message=None, explain=None):
            self._json({'ok': False, 'error': self.responses.get(
                code, ('HTTP error',))[0]}, code)

        def _header(self, name):
            values = self.headers.get_all(name, [])
            if len(values) > 1:
                raise HTTPError(400, f'duplicate {name}')
            return values[0] if values else None

        def _guard(self):
            port = self.server.server_address[1]
            hosts = {f'127.0.0.1:{port}', f'localhost:{port}', f'[::1]:{port}'}
            if port == 80:
                hosts.update(('127.0.0.1', 'localhost', '[::1]'))
            host = self._header('Host')
            if host not in hosts or self.client_address[0] not in ('127.0.0.1', '::1'):
                raise HTTPError(403, 'loopback host required')
            origin = self._header('Origin')
            if origin is not None and origin != f'http://{host}':
                raise HTTPError(403, 'same-origin request required')
            if self.command == 'POST' and origin is None:
                raise HTTPError(403, 'Origin required')
            site = self._header('Sec-Fetch-Site')
            if site not in (None, 'same-origin', 'none'):
                raise HTTPError(403, 'cross-site request denied')
            if len(self.path) > MAX_TARGET:
                raise HTTPError(414, 'request target too long')
            if (not self.path.startswith('/') or self.path.startswith('//')
                    or '\\' in self.path or '#' in self.path
                    or any(ord(c) < 32 or ord(c) == 127 for c in self.path)):
                raise HTTPError(400, 'invalid request target')
            try:
                u = urlsplit(self.path)
                q = parse_qs(u.query, keep_blank_values=True,
                             max_num_fields=8, errors='strict')
            except (ValueError, UnicodeError):
                raise HTTPError(400, 'invalid query') from None
            if u.scheme or u.netloc or any(len(v) != 1 for v in q.values()):
                raise HTTPError(400, 'invalid query')
            if self._header('Transfer-Encoding') is not None:
                raise HTTPError(400, 'Transfer-Encoding unsupported')
            if self._header('Content-Encoding') is not None:
                raise HTTPError(415, 'Content-Encoding unsupported')
            if self._header('Expect') is not None:
                raise HTTPError(417, 'Expect unsupported')
            length = self._header('Content-Length')
            if length is not None:
                if not re.fullmatch(r'[0-9]{1,10}', length):
                    raise HTTPError(400, 'invalid Content-Length')
                if int(length) > MAX_BODY:
                    raise HTTPError(413, 'request body too large')
            if self.command != 'POST' and length not in (None, '0'):
                raise HTTPError(400, 'unexpected request body')
            return u.path, q

        def _body(self):
            length = self._header('Content-Length')
            if length is None:
                raise HTTPError(411, 'Content-Length required')
            ctype = self._header('Content-Type') or ''
            if ctype.split(';', 1)[0].strip().lower() != 'application/json':
                raise HTTPError(415, 'application/json required')
            data = self.rfile.read(int(length))
            if len(data) != int(length):
                raise HTTPError(400, 'incomplete request body')
            try:
                body = json.loads(data.decode('utf-8'),
                                  object_pairs_hook=_json_pairs,
                                  parse_constant=_reject_constant)
            except (ValueError, UnicodeError, RecursionError):
                raise HTTPError(400, 'invalid JSON') from None
            if not isinstance(body, dict):
                raise HTTPError(400, 'JSON object required')
            _json_limits(body)
            return body

        def _dispatch(self):
            try:
                path, q = self._guard()
                if self.command == 'GET':
                    with app.lock:
                        return self._get(path, q)
                if self.command == 'POST':
                    if path not in ('/api/event', '/api/decision', '/api/submit'):
                        raise HTTPError(404, 'not found')
                    if q:
                        raise HTTPError(400, 'unexpected query')
                    body = self._body()
                    with app.lock:
                        return self._post(path, body)
                raise HTTPError(405, 'method not allowed')
            except HTTPError as exc:
                self._json({'ok': False, 'error': str(exc)}, exc.code)
            except StoreError as exc:
                self._json({'ok': False, 'error': str(exc)}, 400)
            except TimeoutError:
                if not self._responded:
                    self._json({'ok': False, 'error': 'request timed out'}, 408)
            except (BrokenPipeError, ConnectionError):
                self.close_connection = True
            except Exception:
                LOGGER.exception('P0 request failed')
                if not self._responded:
                    self._json({'ok': False, 'error': 'internal server error'}, 500)

        do_GET = _dispatch
        do_POST = _dispatch
        do_OPTIONS = _dispatch
        do_HEAD = _dispatch
        do_PUT = _dispatch
        do_DELETE = _dispatch
        do_PATCH = _dispatch

        def _case(self, case_id):
            if not app.authorized_case(case_id):
                raise HTTPError(404, 'case not found')

        def _get(self, path, q):
            rev = app.session['reviewer_id']
            if path in ('/', '/index.html'):
                return self._static('index.html')
            if path.startswith('/static/'):
                return self._static(path[len('/static/'):])
            if path == '/api/session':
                items = []
                for i, it in enumerate(app.session['items']):
                    c = app.cases.get(it['case_id'], {})
                    items.append({**it, 'idx': i, 'isin': c.get('isin'),
                                  'issuer': c.get('issuer'),
                                  'stratum': c.get('stratum')})
                return self._json({'session_id': app.session['session_id'],
                                   'reviewer_id': rev, 'items': items})
            if path == '/api/schema':
                return self._json(SCHEMA)
            match = re.fullmatch(rf'/api/(case|audit)/({IDENTIFIER})', path)
            if match:
                kind, cid = match.groups()
                self._case(cid)
                if kind == 'case':
                    return self._json(app.case_payload(cid, rev))
                decs = app.store.decisions_for(cid, rev)
                ptrs = [p for d in decs for p in d.get('evidence_pointers', [])]
                return self._json(ev_mod.audit_case(cid, ptrs, app.case_documents(cid)))
            match = re.fullmatch(
                rf'/api/doc/({IDENTIFIER})/(meta|file|search|page/([^/]+)\.png)', path)
            if not match:
                raise HTTPError(404, 'not found')
            doc, action, page = match.groups()
            if not app.authorized_doc(doc):
                raise HTTPError(404, 'document not found')
            if action == 'meta':
                meta = app.doc_meta(doc)
                if meta is None:
                    raise HTTPError(404, 'document not found')
                return self._json(meta)
            if action == 'file':
                pdf = cases_mod.pdf_path(doc)
                if pdf is None:
                    raise HTTPError(404, 'document not found')
                with pdf.open('rb') as source:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/pdf')
                    self.send_header('Content-Length', str(os.fstat(source.fileno()).st_size))
                    self.end_headers()
                    while chunk := source.read(65536):
                        self.wfile.write(chunk)
                return
            if action == 'search':
                query = q.get('q', [''])[0]
                if len(query) > MAX_QUERY:
                    raise HTTPError(400, 'search query too long')
                return self._json(app.search_doc(doc, query))
            if not re.fullmatch(r'[0-9]{1,5}', page):
                raise HTTPError(400, 'invalid page')
            try:
                scale = float(q.get('scale', ['1.6'])[0])
            except ValueError:
                raise HTTPError(400, 'invalid scale') from None
            png = app.render_page(doc, int(page), scale)
            if png is None:
                raise HTTPError(404, 'page not found')
            return self._send(png, 'image/png')

        def _post(self, path, body):
            cid = body.get('case_id')
            if not _identifier(cid):
                raise HTTPError(400, 'invalid case_id')
            self._case(cid)
            rev = app.session['reviewer_id']
            docs = app.case_documents(cid)
            if path == '/api/event':
                _string(body.get('event_type'), 'event_type')
                payload = body.get('payload')
                if payload is not None and not isinstance(payload, dict):
                    raise HTTPError(400, 'payload must be an object')
                for name in ('doc_id', 'from', 'to'):
                    if payload and name in payload and (
                            not _identifier(payload[name]) or payload[name] not in docs):
                        raise HTTPError(400, 'event document not authorized')
                ev = app.store.record_event(rev, cid, body['event_type'], payload)
                return self._json({'ok': True, 'event': ev})
            if path == '/api/decision':
                for name in ('field', 'decision'):
                    _string(body.get(name), name)
                _string(body.get('candidate_id'), 'candidate_id', 256, optional=True)
                _string(body.get('origin', 'MACHINE_CANDIDATE'), 'origin')
                if body['field'] not in {f['id'] for f in SCHEMA['fields']}:
                    raise HTTPError(400, 'unknown field')
                pointers = body.get('evidence_pointers')
                if pointers is not None and (not isinstance(pointers, list)
                                             or len(pointers) > 64):
                    raise HTTPError(400, 'invalid evidence_pointers')
                for pointer in pointers or []:
                    if not isinstance(pointer, dict) or not _identifier(pointer.get('doc_id')):
                        raise HTTPError(400, 'invalid evidence pointer')
                    if pointer['doc_id'] not in docs:
                        raise HTTPError(400, 'evidence document not authorized')
                candidates = (app.cases[cid].get('candidates', [])
                              if app.assigned_mode(cid) == 'ASSISTED' else [])
                dec = app.store.record_decision(
                    rev, cid, body['field'], body['decision'], body.get('value'),
                    body.get('candidate_id'), body.get('origin', 'MACHINE_CANDIDATE'),
                    pointers, case_candidates=candidates, case_documents=docs)
                return self._json({'ok': True, 'decision': dec})
            notes = body.get('reviewer_notes')
            if notes is not None and (not isinstance(notes, list) or len(notes) > 64
                                      or any(not isinstance(n, str) for n in notes)):
                raise HTTPError(400, 'reviewer_notes must be a list of strings')
            review = app.store.submit_review(rev, cid, SCHEMA,
                                             reviewer_notes=notes, case_documents=docs)
            app.save_completed(cid)
            return self._json({'ok': True, 'review': review})

        def _static(self, name):
            types = {'index.html': 'text/html; charset=utf-8',
                     'app.js': 'text/javascript; charset=utf-8',
                     'style.css': 'text/css; charset=utf-8'}
            if name not in types:
                raise HTTPError(404, 'not found')
            p = STATIC / name
            if p.is_symlink() or p.resolve().parent != STATIC.resolve() or not p.is_file():
                raise HTTPError(404, 'not found')
            return self._send(p.read_bytes(), types[name])

    return H


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--session', required=True)
    ap.add_argument('--port', type=int, default=8765)
    args = ap.parse_args()
    app = App(args.session)
    try:
        with ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(app)) as srv:
            srv.daemon_threads = False
            print(f'P0 reviewer app: http://127.0.0.1:{srv.server_port} '
                  f'session={app.session["session_id"]}')
            try:
                srv.serve_forever()
            except KeyboardInterrupt:
                pass
    finally:
        app.close()


if __name__ == '__main__':
    sys.exit(main())
