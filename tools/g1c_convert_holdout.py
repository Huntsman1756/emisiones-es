"""G1-C: conversion Docling de los PDFs del extraction holdout G1.

Escribe .work/docling-g1-holdout/<key>.json + performance por doc.
Solo conversion; cero cambios de pipeline.
"""
import json, time, warnings
from pathlib import Path

import psutil

warnings.filterwarnings('ignore')

EH = 'g1/manifests/g1-a1/extraction-holdout.json'
OUT = Path('.work/docling-g1-holdout')
OUT.mkdir(parents=True, exist_ok=True)
PERF = Path('g1/results/performance-docling-holdout.json')
PERF.parent.mkdir(parents=True, exist_ok=True)

man = json.load(open(EH, encoding='utf-8'))
from docling.document_converter import DocumentConverter
conv = DocumentConverter()
proc = psutil.Process()

results = []
if PERF.exists():
    results = json.load(open(PERF, encoding='utf-8'))['documents']
done = {r['doc'] for r in results}

for d in man['docs']:
    key = d['source_record_key']
    pdf = Path(d['local_evidence'])
    if key in done or not pdf.exists():
        continue
    rec = {'doc': key, 'pages_expected': d.get('pages'),
           'pdf_sha256': d.get('document_sha256')}
    rss0 = proc.memory_info().rss
    t0 = time.time()
    try:
        r = conv.convert(str(pdf))
        doc = r.document
        rec.update(status='ok', seconds=round(time.time() - t0, 2),
                   peak_rss_mb=round((proc.memory_info().rss - rss0) / 1e6, 1),
                   pages=len(doc.pages), texts=len(doc.texts),
                   tables=len(doc.tables))
        doc.save_as_json(OUT / f'{key}.json')
    except Exception as e:
        rec.update(status='error', error=str(e)[:300],
                   seconds=round(time.time() - t0, 2))
    results.append(rec)
    json.dump({'phase': 'G1-C docling conversion extraction holdout',
               'documents': results},
              open(PERF, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(key, rec.get('status'), rec.get('seconds'), 's',
          rec.get('pages'), 'pp', flush=True)
