"""G0-D: ejecuta los extractores congelados (olas 1+2) sobre los 30
documentos extraction-holdout ya convertidos (.work/docling-holdout/X*.json).

Salida: g0/results/g0-d-extraction-predictions.json (se sella con sha256
antes de anotar truth). Una sola ejecucion; sin retries semánticos.
"""
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, 'src')
from docling_core.types.doc import DoclingDocument
from emissions_es.extraction.docview import NormalizedDocumentView
from emissions_es.extraction.extractors import extract_all

man = json.load(open('g0/manifests/extraction-holdout.json',
                     encoding='utf-8'))
DL = Path('.work/docling-holdout')
run_id = 'g0d-' + uuid.uuid4().hex[:12]
code_freeze = json.load(open('g0/code-freeze.json', encoding='utf-8'))

docs = []
for c in man['cases']:
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.time()
    rec = {'case_key': c['case_key'], 'stratum': c['stratum'],
           'issuer': c['issuer'], 'document_role': c['document_role'],
           'instrument_class': c['instrument_class'],
           'source_record_key': c['source_record_key'],
           'input_document_sha256': (c.get('downloaded') or {}).get('sha256'),
           'run_id': run_id, 'started_at': started,
           'fields': [], 'docling_ok': False}
    cand = [p for p in DL.glob('X*.json')
            if p.stem.startswith(c['case_key'] + '_')]
    if not cand:
        rec['eval_status'] = 'INVALID_EVALUATION'
        rec['note'] = 'docling json no disponible'
        docs.append(rec)
        continue
    d = DoclingDocument.load_from_json(str(cand[0]))
    v = NormalizedDocumentView(d, c['source_family'],
                             c['source_record_key'],
                             rec['input_document_sha256'])
    obs = extract_all(v, doc_role=c['document_role'])
    rec['docling_ok'] = True
    rec['eval_status'] = 'ok'
    rec['fields'] = [
        {'field': o.field, 'status': o.status.value,
         'value': (o.value if not isinstance(o.value, dict)
                   else f"{o.value.get('amount')} {o.value.get('currency')}"),
         'raw_lexeme': o.raw_lexeme,
         'confidence_class': o.confidence_class,
         'n_evidence': len(o.evidence),
         'evidence': [{'page': e.page, 'source': e.source,
                       'source_record_key': e.source_record_key,
                       'snapshot_sha256': e.snapshot_sha256,
                       'bbox': e.bbox, 'charspan': e.charspan,
                       'excerpt': e.text_excerpt,
                       'extractor': e.extractor,
                       'extractor_version': e.extractor_version}
                      for e in o.evidence],
         'extractor': o.extractor, 'extractor_version': o.extractor_version}
        for o in obs]
    rec['runtime_s'] = round(time.time() - t0, 3)
    rec['finished_at'] = datetime.now(timezone.utc).isoformat()
    docs.append(rec)
    got = [f for f in rec['fields'] if f['status'] in
           ('DERIVED', 'OBSERVED', 'CONFLICT')]
    print(c['case_key'], c['source_record_key'], '->', len(got), 'campos',
          flush=True)

from collections import Counter
agg = Counter()
for d in docs:
    for f in d['fields']:
        agg[(f['field'], f['status'])] += 1
summary = {f'{k[0]}|{k[1]}': n for k, n in sorted(agg.items())}

out = {'manifest': 'extraction-holdout.json',
       'run_id': run_id,
       'code_freeze': {'commit': code_freeze['frozen_at_commit'],
                       'extractor_registry_sha256':
                           code_freeze['code']['extractor_registry_sha256'],
                       'normalizers_sha256':
                           code_freeze['code']['normalizers_sha256']},
       'status_summary': summary,
       'documents': docs}
p = Path('g0/results/g0-d-extraction-predictions.json')
p.write_text(json.dumps(out, ensure_ascii=False, indent=1,
                      default=str), encoding='utf-8')
import hashlib
print('predictions_sha256:',
      hashlib.sha256(p.read_bytes()).hexdigest())
print(json.dumps(summary, indent=0))
