"""P0 mechanical ingest — RUN ONLY AFTER p0/ui-freeze.json exists.

Per protocol §18: fetch frozen sample PDFs, convert with the frozen
Docling version, build IR with the frozen G2-A adapter, run the frozen
classifier+extractor, seal p0/candidates/<case>.json with SHA.

Results are never inspected to improve code (P0-B §1, §18).

  python p0/ingest_p0.py
"""
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / '.work' / 'g2a' / 'ir'))

SAMPLE = REPO / 'p0' / 'manifests' / 'sample.json'
FREEZE = REPO / 'p0' / 'ui-freeze.json'
DOCS = REPO / 'p0' / 'docs'
DL = REPO / 'p0' / 'docling'
IRD = REPO / 'p0' / 'ir'
CAND = REPO / 'p0' / 'candidates'

UA = {'User-Agent': 'Mozilla/5.0 (emisiones-es research)'}


def candidates_from_fields(doc_key, fields):
    """Extractor output -> candidate list (same shape as dev cases)."""
    out = []
    for fname, fobj in fields.items():
        obs = fobj.get('observation') or {}
        if obs.get('status') not in ('DERIVED', 'OBSERVED', 'CONFLICT'):
            continue
        if obs.get('value') in (None, '', []):
            continue
        evs = [{'doc_id': ev.get('source_record_key') or doc_key,
                'page': ev.get('page'), 'bbox': ev.get('bbox'),
                'excerpt': ev.get('text_excerpt'),
                'sha256': ev.get('snapshot_sha256')}
               for ev in obs.get('evidence', [])]
        out.append({'candidate_id': f'{doc_key}:{fname}',
                    'field': fname, 'value': obs.get('value'),
                    'raw_lexeme': obs.get('raw_lexeme'),
                    'state': 'CANDIDATE',
                    'observation_status': obs.get('status'),
                    'confidence_class': obs.get('confidence_class'),
                    'evidence': evs})
    return out


def main():
    if not FREEZE.exists():
        sys.exit('REFUSED: p0/ui-freeze.json missing — freeze UI first')
    for d in (DOCS, DL, IRD, CAND):
        d.mkdir(exist_ok=True)
    sample = json.load(open(SAMPLE, encoding='utf-8'))

    from docling.document_converter import DocumentConverter
    from docling_core.types.doc import DoclingDocument
    from adapter_docling import from_docling_json
    from ir import derive_relations
    from emissions_es.classification.dispatcher import (
        SourceDocument, classify)
    from emissions_es.extraction.docview import NormalizedDocumentView
    from emissions_es.extraction.dispatcher import (
        extract_document, extractor_for)

    conv = DocumentConverter()
    for c in sample['cases'] + sample['warmup_cases']:
        cid, key = c['case_id'], c['source_record_key']

        pdf = DOCS / f'{key}.pdf'
        if not pdf.exists():
            req = urllib.request.Request(c['document_url'], headers=UA)
            pdf.write_bytes(urllib.request.urlopen(req, timeout=90).read())
            time.sleep(0.5)
        sha = hashlib.sha256(pdf.read_bytes()).hexdigest()

        dl_json = DL / f'{key}.json'
        if not dl_json.exists():
            doc = conv.convert(str(pdf)).document
            dl_json.write_text(json.dumps(
                doc.export_to_dict(), ensure_ascii=False))
        doc = DoclingDocument.load_from_json(str(dl_json))

        ir_file = IRD / f'{key}.ir.json'
        if not ir_file.exists():
            ir = derive_relations(from_docling_json(
                doc.export_to_dict(), key))
            ir_file.write_text(json.dumps(
                ir.to_dict(), ensure_ascii=False))

        view = NormalizedDocumentView(doc, 'CNMV_ADMISSION', key, sha)
        sdoc = SourceDocument(
            source_record_key=key,
            acquisition_surface='CNMV_ADMISSION',
            registro_oficial=c.get('numfol'), numfol=c.get('numfol'),
            issuer_key=c.get('issuer'),
            source_meta={'denominacion': c.get('denominacion'),
                         'rol': 'ADMISSION'})
        sdoc.head_text = (view.text() or '')[:4000]
        cl = classify(sdoc)
        res = extract_document(view, cl)
        fields = {}
        for f, er in res.items():
            if f.startswith('_'):
                continue
            fields[f] = {
                'observation': er.observation.model_dump(mode='json')
                if er.observation else None,
                'failure': er.failure.value if er.failure else None,
                'failure_detail': er.failure_detail,
                'located_regions': er.located_regions}

        out = {
            'case_id': cid, 'source_record_key': key,
            'document_sha256': sha,
            'classification': {
                'document_role': cl.document_role,
                'scope_role': cl.scope_role,
                'instrument_class': cl.instrument_class,
                'document_family_key': cl.document_family_key,
                'confidence': cl.confidence},
            'extractor': (extractor_for(cl).family_id
                          if extractor_for(cl) else None),
            'graph': {'status': 'INCOMPLETE', 'nodes': [
                {'id': key, 'role': cl.document_role,
                 'issuer': c['issuer'], 'observed': True,
                 'is_case_doc': True}],
                'edges': [], 'missing_expected_documents': []},
            'candidates': candidates_from_fields(key, fields),
        }
        blob = json.dumps(out, ensure_ascii=False, sort_keys=True).encode()
        out['candidate_file_sha256'] = hashlib.sha256(blob).hexdigest()
        (CAND / f'{cid}.json').write_text(
            json.dumps(out, ensure_ascii=False, indent=1))
        print('sealed', cid, cl.document_role, len(out['candidates']),
              'candidates', flush=True)


if __name__ == '__main__':
    main()
