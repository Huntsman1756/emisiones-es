"""Ejecuta los extractores deterministas (olas 1+2) sobre los
documentos extraction-deep-dev ya convertidos (.work/docling/D*.json).
NO toca el holdout."""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, 'src')
from docling_core.types.doc import DoclingDocument
from emissions_es.extraction.docview import NormalizedDocumentView
from emissions_es.extraction.extractors import extract_all

man = json.load(open('g0/manifests/extraction-deep-dev.json',
                     encoding='utf-8'))
DL = Path('.work/docling')

docs = []
for c in man['cases']:
    rec = {'case_key': c['case_key'], 'stratum': c['stratum'],
           'issuer': c['issuer'], 'document_role': c['document_role'],
           'instrument_class': c['instrument_class'],
           'source_record_key': c['source_record_key'],
           'fields': [], 'docling_ok': False}
    cand = [p for p in DL.glob('D*.json')
            if p.stem.startswith(c['case_key'] + '_')]
    if not cand:
        rec['note'] = 'docling json no disponible'
        docs.append(rec)
        continue
    d = DoclingDocument.load_from_json(str(cand[0]))
    sha = (c.get('downloaded') or {}).get('sha256')
    v = NormalizedDocumentView(d, c['source_family'],
                             c['source_record_key'], sha)
    obs = extract_all(v, doc_role=c['document_role'])
    rec['docling_ok'] = True
    rec['fields'] = [
        {'field': o.field, 'status': o.status.value,
         'value': (f"{o.value.get('amount')} {o.value.get('currency')}"
                   if isinstance(o.value, dict)
                   else (str(o.value) if o.value is not None else None)),
         'raw_lexeme': o.raw_lexeme,
         'n_evidence': len(o.evidence),
         'page': o.evidence[0].page if o.evidence else None,
         'extractor': o.extractor, 'extractor_version': o.extractor_version}
        for o in obs]
    docs.append(rec)
    got = [f for f in rec['fields'] if f['status'] in
           ('DERIVED', 'OBSERVED', 'CONFLICT')]
    print(c['case_key'], c['source_record_key'], '->', len(got), 'campos',
          flush=True)

agg = Counter()
for d in docs:
    for f in d['fields']:
        agg[(f['field'], f['status'])] += 1
summary = {f'{k[0]}|{k[1]}': n for k, n in sorted(agg.items())}

json.dump({'manifest': 'extraction-deep-dev.json',
           'manifest_sha256': man['manifest_sha256'],
           'wave': 'first+second (G0-C.1 deep contractual terms)',
           'status_summary': summary,
           'documents': docs},
          open('g0/results/extraction-deep-dev-results.json', 'w',
               encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(summary, indent=0))
