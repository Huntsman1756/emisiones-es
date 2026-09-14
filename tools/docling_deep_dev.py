"""Convierte los 13 docs extraction-deep-dev (D*.pdf) con Docling y
cachea los DoclingDocument en .work/docling/. Misma configuracion de
pipeline que el baseline G0-C (DocumentConverter por defecto).
"""
import json
import sys
import time
import warnings
from pathlib import Path

import psutil

warnings.filterwarnings('ignore')

SNAP = Path('g0/snapshots')
OUT = Path('.work/docling'); OUT.mkdir(parents=True, exist_ok=True)
RESULTS = Path('g0/results/docling-deep-dev.json')

files = sorted(SNAP.glob('D*.pdf'))
assert files, 'sin documentos deep-dev'

from docling.document_converter import DocumentConverter
conv = DocumentConverter()
proc = psutil.Process()

results = []
if RESULTS.exists():
    results = json.load(open(RESULTS, encoding='utf-8'))['documents']
done = {r['file'] for r in results}

for f in files:
    if f.name in done:
        continue
    rec = {'file': f.name, 'bytes': f.stat().st_size}
    rss0 = proc.memory_info().rss
    t0 = time.time()
    try:
        r = conv.convert(str(f))
        d = r.document
        rec.update(status='ok', seconds=round(time.time() - t0, 2),
                   peak_rss_mb=round((proc.memory_info().rss - rss0) / 1e6, 1),
                   pages=len(d.pages), texts=len(d.texts),
                   tables=len(d.tables),
                   key_value_items=len(getattr(d, 'key_value_items', []) or []))
        d.save_as_json(OUT / f'{f.stem}.json')
    except Exception as e:
        rec.update(status='error', error=str(e)[:300],
                   seconds=round(time.time() - t0, 2))
    results.append(rec)
    json.dump({'phase': 'G0-C.1 deep-dev conversion',
               'docling_version': __import__('docling').__version__,
               'documents': results},
              open(RESULTS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f.name, rec.get('status'), rec.get('seconds'), 's',
          'pages', rec.get('pages'), 'texts', rec.get('texts'),
          'tables', rec.get('tables'), flush=True)
