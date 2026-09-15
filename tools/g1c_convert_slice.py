"""G1-C: worker paralelo de conversion Docling (operacional, mismo code path).

Uso: python tools/g1c_convert_slice.py <slice_idx> <n_slices>
Cada worker convierte docs[slice_idx::n_slices] en orden inverso para
minimizar solapamiento con el worker principal (orden directo).
Escribe .work/docling-g1-holdout/<key>.json (identico) +
g1/results/performance-docling-slice-<idx>.json (merge posterior).
"""
import json, sys, time, warnings
from pathlib import Path

import psutil

warnings.filterwarnings('ignore')

EH = 'g1/manifests/g1-a1/extraction-holdout.json'
OUT = Path('.work/docling-g1-holdout')
OUT.mkdir(parents=True, exist_ok=True)

idx, n = int(sys.argv[1]), int(sys.argv[2])
PERF = Path(f'g1/results/performance-docling-slice-{idx}.json')

man = json.load(open(EH, encoding='utf-8'))
docs = man['docs'][idx::n]
if idx != 0:
    docs = list(reversed(docs))

from docling.document_converter import DocumentConverter
conv = DocumentConverter()
proc = psutil.Process()

results = []
if PERF.exists():
    results = json.load(open(PERF, encoding='utf-8'))['documents']
done = {r['doc'] for r in results}

for d in docs:
    key = d['source_record_key']
    pdf = Path(d['local_evidence'])
    if key in done or not pdf.exists():
        continue
    if (OUT / f'{key}.json').exists():
        done.add(key)
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
    json.dump({'phase': f'G1-C docling conversion slice {idx}',
               'documents': results},
              open(PERF, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(idx, key, rec.get('status'), rec.get('seconds'), 's', flush=True)
