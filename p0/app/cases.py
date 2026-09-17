"""Case assembly for the reviewer app.

DEVELOPMENT cases are built from frozen G1 artifacts (development docs,
extraction predictions as machine candidates, family-map + linkage
predictions as document graph). P0 cases are loaded from the frozen
sample manifest + sealed candidate artifacts (generated post-UI-freeze).

No P0 holdout document is inspected here beyond mechanical ingest.
"""
import hashlib
import json
import re
from copy import deepcopy
from threading import RLock
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = REPO / 'g1' / 'snapshots'
IR_DIR = REPO / '.work' / 'g2a' / 'ir' / 'docling'
P0_DOCS_DIR = REPO / 'p0' / 'docs'
P0_CAND_DIR = REPO / 'p0' / 'candidates'

# roles an instrument case is expected to have when resolvable
EXPECTED_ROLES_BY_CONTEXT = {
    'FINAL_TERMS': ['BASE_PROSPECTUS', 'ADMISSION'],
    'ISSUE_DOC': ['ADMISSION'],
    'SECURITIES_NOTE': ['ADMISSION'],
}

_cache = {}
_cache_lock = RLock()


def valid_doc_id(doc_key):
    return isinstance(doc_key, str) and re.fullmatch(
        r'[A-Za-z0-9][A-Za-z0-9_-]{0,199}', doc_key) is not None


def _load(name, path):
    path = Path(path).resolve()
    stat = path.stat()
    key = (name, path, stat.st_mtime_ns, stat.st_size)
    with _cache_lock:
        if key not in _cache:
            with path.open(encoding='utf-8') as f:
                _cache[key] = json.load(f)
        return deepcopy(_cache[key])


def document_ids(case):
    docs = set(case.get('documents', []))
    if case.get('primary_doc'):
        docs.add(case['primary_doc'])
    docs.update(n['id'] for n in (case.get('graph') or {}).get('nodes', [])
                if n.get('observed'))
    return {d for d in docs if valid_doc_id(d)}


def _family_map():
    return _load('family_map', REPO / 'g1' / 'manifests' / 'family-map.json')


def _predictions():
    return _load('ext_pred', REPO / 'g1' / 'results'
                 / 'extraction-predictions.json')


def _linkage():
    return _load('linkage', REPO / 'g1' / 'results'
                 / 'linkage-predictions.json')


def _dev_manifest():
    return _load('dev', REPO / 'g1' / 'manifests' / 'development.json')


def _fetch_index():
    return _load('fetch', REPO / 'g1' / 'manifests' / 'fetch-index.json')


def _records_by_key():
    return {r['key']: r for r in _family_map()['records']}


def _pool_meta():
    return {d['source_record_key']: d
            for d in _dev_manifest().get('new_pool_docs', [])}


def _contained_file(base, name):
    base = Path(base).resolve()
    path = (base / name).resolve()
    return path if path.parent == base and path.is_file() else None


def pdf_path(doc_key):
    if not valid_doc_id(doc_key):
        return None
    for base in (SNAPSHOT_DIR, P0_DOCS_DIR):
        p = _contained_file(base, f'{doc_key}.pdf')
        if p:
            return p
    return None


def ir_path(doc_key):
    if not valid_doc_id(doc_key):
        return None
    for base in (IR_DIR, REPO / 'p0' / 'ir'):
        p = _contained_file(base, f'{doc_key}.ir.json')
        if p:
            return p
    return None


def _sealed_candidate(cid):
    if not valid_doc_id(cid):
        raise ValueError('invalid case id')
    path = _contained_file(P0_CAND_DIR, f'{cid}.json')
    if path is None:
        return None
    raw = path.read_bytes()
    seal = _load('candidate_seal', REPO / 'p0/results/candidate-seal.json')
    expected = next((c['sha256'] for c in seal['cases']
                     if c['case_id'] == cid), None)
    if expected is None or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f'candidate seal mismatch: {cid}')
    obj = json.loads(raw)
    declared = obj.pop('candidate_file_sha256', None)
    actual = hashlib.sha256(json.dumps(
        obj, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    if declared != actual or obj.get('case_id') != cid:
        raise ValueError(f'candidate content seal mismatch: {cid}')
    obj['candidate_file_sha256'] = declared
    return obj


def doc_sha256(doc_key):
    if not valid_doc_id(doc_key):
        return None
    for f in _fetch_index()['fetches']:
        if f['doc_id'] == doc_key:
            return f['sha256']
    sample = _load('p0_sample', REPO / 'p0/manifests/sample.json')
    for c in sample['cases'] + sample['warmup_cases']:
        if c['source_record_key'] == doc_key:
            sealed = _sealed_candidate(c['case_id'])
            if sealed and sealed.get('source_record_key') == doc_key:
                return sealed.get('document_sha256')
    return None


def _candidate_from_field(field_name, field_obj, doc_key):
    obs = field_obj.get('observation') or {}
    if obs.get('status') not in ('DERIVED', 'OBSERVED', 'CONFLICT'):
        return None
    if obs.get('value') in (None, '', []):
        return None
    evs = []
    for ev in obs.get('evidence', []):
        src = ev.get('source_record_key') or doc_key
        evs.append({
            'doc_id': src,
            'page': ev.get('page'),
            'bbox': ev.get('bbox'),
            'excerpt': ev.get('text_excerpt'),
            'sha256': ev.get('snapshot_sha256'),
        })
    return {
        'candidate_id': f'{doc_key}:{field_name}',
        'field': field_name,
        'value': obs.get('value'),
        'raw_lexeme': obs.get('raw_lexeme'),
        'state': 'CANDIDATE',
        'observation_status': obs.get('status'),
        'confidence_class': obs.get('confidence_class'),
        'evidence': evs,
    }


def _build_graph(doc_key):
    """Nodes = family-map records sharing the doc's family.
    Edges = linkage predictions on family members. Never fabricate."""
    rec = _records_by_key().get(doc_key)
    if not rec:
        return {'status': 'INCOMPLETE', 'nodes': [], 'edges': [],
                'missing_expected_documents': ['FAMILY_UNKNOWN']}
    fam = [r for r in _family_map()['records']
           if r['family'] == rec['family']]
    nodes = [{
        'id': r['key'], 'role': r['role'], 'issuer': r['issuer'],
        'observed': pdf_path(r['key']) is not None,
        'is_case_doc': r['key'] == doc_key,
    } for r in fam]
    node_ids = {n['id'] for n in nodes}

    edges = []
    for p in _linkage()['predictions']:
        if p['source_key'] not in node_ids or p['decision'] == 'NO_LINK':
            continue
        cand = p['candidate'] or {}
        numfol = cand.get('numfol')
        target = None
        if numfol:
            for n in nodes:
                if numfol in n['id'] and n['id'] != p['source_key']:
                    if cand['type'].startswith('base') and \
                            n['role'] == 'BASE_PROSPECTUS':
                        target = n['id']
                    elif cand['type'].startswith('final') and \
                            n['role'] == 'FINAL_TERMS':
                        target = n['id']
        if target is None and cand['type'] == 'family':
            bps = [n for n in nodes if n['role'] == 'BASE_PROSPECTUS']
            target = bps[0]['id'] if bps else None
        if target:
            edges.append({
                'from': p['source_key'], 'to': target,
                'relation': p.get('relation') or 'RELATES_TO',
                'state': p['decision'],           # AUTO_LINKED|REVIEW_REQUIRED
                'rule_id': p.get('rule_id'),
            })

    case_role = rec['role']
    present = {n['role'] for n in nodes}
    missing = [r for r in EXPECTED_ROLES_BY_CONTEXT.get(case_role, [])
               if r not in present]
    status = 'COMPLETE' if not missing and edges else 'INCOMPLETE'
    return {
        'status': status, 'family': rec['family'],
        'nodes': nodes, 'edges': edges,
        'graph_nodes_found': len(nodes),
        'graph_edges_found': len(edges),
        'review_required_edges': sum(1 for e in edges
                                     if e['state'] == 'REVIEW_REQUIRED'),
        'missing_expected_documents': missing,
    }


def build_dev_cases():
    """One dev case per G1 extraction-development doc with IR."""
    cases = {}
    pool = _pool_meta()
    for d in _predictions()['documents']:
        if not d.get('docling'):
            continue
        key = d['doc']
        meta = pool.get(key, {})
        fields = d.get('fields', {})
        candidates = []
        for fname, fobj in fields.items():
            c = _candidate_from_field(fname, fobj, key)
            if c:
                candidates.append(c)
        cases[key] = {
            'case_id': key,
            'case_class': 'DEVELOPMENT',
            'isin': meta.get('isin') or _field_value(fields, 'isin'),
            'issuer': meta.get('issuer', ''),
            'instrument_class': meta.get('instrument_class',
                                       d['classification']
                                       .get('instrument_class')),
            'document_role': d['classification'].get('document_role'),
            'primary_doc': key,
            'documents': [key],
            'graph': _build_graph(key),
            'candidates': candidates,
        }
    return cases


def _field_value(fields, name):
    obs = (fields.get(name) or {}).get('observation') or {}
    return obs.get('value')


def build_p0_cases():
    """P0 holdout/warmup cases from the frozen sample manifest.
    Candidates come only from sealed p0/candidates/<case>.json."""
    sample = _load('p0_sample', REPO / 'p0' / 'manifests' / 'sample.json')
    cases = {}
    for c in sample['cases'] + sample['warmup_cases']:
        cid = c['case_id']
        sealed = _sealed_candidate(cid)
        if sealed and sealed.get('source_record_key') != c['source_record_key']:
            raise ValueError(f'candidate document mismatch: {cid}')
        cases[cid] = {
            'case_id': cid,
            'case_class': 'P0_' + c['role'].upper(),
            'isin': c['isin'],
            'issuer': c['issuer'],
            'instrument_class': 'DEBT',
            'document_role': 'ISSUE_DOC',
            'stratum': c['stratum'],
            'primary_doc': c['source_record_key'],
            'documents': [c['source_record_key']],
            'document_url': c['document_url'],
            'graph': sealed.get('graph') if sealed else
            {'status': 'INCOMPLETE', 'nodes': [], 'edges': [],
             'missing_expected_documents': []},
            'candidates': sealed.get('candidates', []) if sealed else [],
            'candidates_sealed': sealed is not None,
        }
    return cases


def all_cases():
    cases = build_dev_cases()
    try:
        cases.update(build_p0_cases())
    except FileNotFoundError:
        pass
    return cases


def ir_for(doc_key):
    p = ir_path(doc_key)
    if not p:
        return None
    return json.load(open(p, encoding='utf-8'))
