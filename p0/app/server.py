"""P0 reviewer app — stdlib HTTP server.

  python -m p0.app.server --session p0/runtime/session_dev_xxx.json \
      --port 8765

Mode is enforced server-side from the session item; the client cannot
switch a case between MANUAL and ASSISTED.
"""
import io
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from . import cases as cases_mod
from . import evidence as ev_mod
from . import models
from .store import ReviewStore, StoreError

REPO = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).parent / 'static'
SCHEMA = json.load(open(REPO / 'p0' / 'manifests' / 'review-schema.json',
                        encoding='utf-8'))
PAGECACHE = REPO / 'p0' / 'runtime' / 'pagecache'


class App:
    def __init__(self, session_path):
        self.session_path = Path(session_path)
        self.session = json.load(open(self.session_path, encoding='utf-8'))
        self.cases = cases_mod.all_cases()
        self.store = ReviewStore(self.session_path.parent
                                 / self.session['session_id'])
        self._pdfium = {}

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
        PAGECACHE.mkdir(parents=True, exist_ok=True)
        cache = PAGECACHE / f'{doc_id}_{page_no}_{scale}.png'
        if cache.exists():
            return cache.read_bytes()
        pdf_path = cases_mod.pdf_path(doc_id)
        if pdf_path is None:
            return None
        import pypdfium2 as pdfium
        doc = self._pdfium.get(doc_id)
        if doc is None:
            doc = pdfium.PdfDocument(str(pdf_path))
            self._pdfium[doc_id] = doc
        if not (1 <= page_no <= len(doc)):
            return None
        page = doc[page_no - 1]
        png = page.render(scale=scale).to_pil()
        buf = io.BytesIO()
        png.save(buf, 'PNG')
        data = buf.getvalue()
        cache.write_bytes(data)
        return data

    def doc_meta(self, doc_id):
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
            doc = pdfium.PdfDocument(str(pdf))
            meta['pages'] = [{'page_no': i + 1,
                              'width': doc[i].get_width(),
                              'height': doc[i].get_height()}
                             for i in range(len(doc))]
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
        def log_message(self, *a):
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            n = int(self.headers.get('Content-Length') or 0)
            return json.loads(self.rfile.read(n) or b'{}')

        def do_GET(self):
            u = urlparse(self.path)
            path, q = u.path, parse_qs(u.query)
            rev = app.session['reviewer_id']
            if path == '/' or path == '/index.html':
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
            if path.startswith('/api/case/'):
                cid = path.rsplit('/', 1)[-1]
                payload = app.case_payload(cid, rev)
                return self._json(payload or {'error': 'not found'},
                                  404 if payload is None else 200)
            if path.startswith('/api/doc/') and path.endswith('/meta'):
                doc = path.split('/')[3]
                meta = app.doc_meta(doc)
                return self._json(meta or {'error': 'no doc'},
                                  404 if meta is None else 200)
            if path.startswith('/api/doc/') and path.endswith('/file'):
                doc = path.split('/')[3]
                pdf = cases_mod.pdf_path(doc)
                if pdf is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                body = pdf.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path.startswith('/api/doc/') and path.endswith('/search'):
                doc = path.split('/')[3]
                return self._json(app.search_doc(doc, q.get('q', [''])[0]))
            if path.startswith('/api/doc/') and '.png' in path:
                # /api/doc/<doc>/page/<n>.png?scale=
                parts = path.split('/')
                doc = parts[3]
                page_no = int(parts[5].replace('.png', ''))
                scale = float(q.get('scale', ['1.6'])[0])
                png = app.render_page(doc, page_no, scale)
                if png is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Content-Length', str(len(png)))
                self.end_headers()
                self.wfile.write(png)
                return
            if path.startswith('/api/audit/'):
                cid = path.rsplit('/', 1)[-1]
                decs = app.store.decisions_for(cid, rev)
                ptrs = [p for d in decs for p in
                        d.get('evidence_pointers', [])]
                return self._json(ev_mod.audit_case(cid, ptrs))
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            u = urlparse(self.path)
            body = self._body()
            rev = app.session['reviewer_id']
            try:
                if u.path == '/api/event':
                    ev = app.store.record_event(
                        rev, body['case_id'], body['event_type'],
                        body.get('payload'))
                    return self._json({'ok': True, 'event': ev})
                if u.path == '/api/decision':
                    case = app.cases.get(body['case_id'], {})
                    dec = app.store.record_decision(
                        rev, body['case_id'], body['field'],
                        body['decision'], body.get('value'),
                        body.get('candidate_id'),
                        body.get('origin', 'MACHINE_CANDIDATE'),
                        body.get('evidence_pointers'),
                        case_candidates=case.get('candidates'))
                    return self._json({'ok': True, 'decision': dec})
                if u.path == '/api/submit':
                    review = app.store.submit_review(
                        rev, body['case_id'], SCHEMA,
                        reviewer_notes=body.get('reviewer_notes'))
                    for i, it in enumerate(app.session['items']):
                        if it['case_id'] == body['case_id']:
                            app.session['items'][i]['status'] = 'DONE'
                    json.dump(app.session,
                              open(app.session_path, 'w'), indent=1)
                    return self._json({'ok': True, 'review': review})
            except StoreError as e:
                return self._json({'ok': False, 'error': str(e)}, 400)
            except (KeyError, TypeError) as e:
                return self._json({'ok': False, 'error': str(e)}, 400)
            self.send_response(404)
            self.end_headers()

        def _static(self, name):
            p = STATIC / name
            if not p.exists() or p.parent != STATIC:
                self.send_response(404)
                self.end_headers()
                return
            ctype = ('text/html' if name.endswith('.html') else
                     'text/javascript' if name.endswith('.js') else
                     'text/css' if name.endswith('.css') else
                     'application/octet-stream')
            body = p.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return H


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--session', required=True)
    ap.add_argument('--port', type=int, default=8765)
    args = ap.parse_args()
    app = App(args.session)
    srv = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(app))
    print(f'P0 reviewer app: http://127.0.0.1:{args.port} '
          f'session={app.session["session_id"]}')
    srv.serve_forever()


if __name__ == '__main__':
    sys.exit(main())
