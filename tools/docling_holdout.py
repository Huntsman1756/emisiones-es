"""G0-D: conversion Docling FULL (KEEP_FULL) de los 30 docs extraction-holdout.

Una sola ejecucion; guarda DoclingDocument por doc + performance.
No inspecciona contenido.
"""
import json, sys, time, warnings
from pathlib import Path

import psutil

warnings.filterwarnings('ignore')

SNAP = Path('g0/snapshots')
OUT = Path('.work/docling-holdout'); OUT.mkdir(parents=True, exist_ok=True)
RESULTS = Path('g0/results/g0-d-performance.json')

files = sorted(SNAP.glob('X*.pdf'))
assert len(files) == 30, files

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
                   rss_mb=round((proc.memory_info().rss - rss0) / 1e6, 1),
                   texts=len(d.texts), tables=len(d.tables),
                   kv=len(getattr(d, 'key_value_items', []) or []))
        d.save_as_json(str(OUT / (f.stem + '.json')))
    except Exception as e:
        rec.update(status='error', error=str(e)[:300])
    results.append(rec)
    RESULTS.write_text(json.dumps(
        {'manifest': 'g0-d-performance', 'documents': results}, indent=1),
        encoding='utf-8')
    print(f.name, rec.get('status'), rec.get('seconds'), 's',
          'rss', rec.get('rss_mb'), 'texts', rec.get('texts'),
          'tables', rec.get('tables'), 'kv', rec.get('kv'), flush=True)

print('DONE', len(results))
