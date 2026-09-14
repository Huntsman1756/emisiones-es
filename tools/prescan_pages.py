#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Prescan barato de paginas con pypdf.

Su UNICA funcion es seleccionar paginas candidatas para
Docling(page_range=...); NO produce hechos financieros.

Marca una pagina como candidata si contiene:
  - algun anchor de FIELD_SPECS (etiquetas label->value), o
  - un objeto benchmark identificable, o
  - un ISIN.
Devuelve paginas -> rangos fusionados con contexto +/- CTX.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
from pypdf import PdfReader
from emissions_es.extraction.extractors import FIELD_SPECS
from emissions_es.extraction.normalize import BENCH_RX, ISIN_RX

CTX = 2          # paginas de contexto a cada lado
ANCHOR_RX = re.compile(
    '|'.join('(?:' + a + ')' for s in FIELD_SPECS for a in s.anchors)
    + '|' + BENCH_RX.pattern + '|' + ISIN_RX.pattern,
    re.I)


def scan(pdf_path):
    """-> dict page_no(1-based) -> n_hits, y lista de paginas candidatas."""
    reader = PdfReader(str(pdf_path))
    hits = {}
    for i, page in enumerate(reader.pages, start=1):
        try:
            txt = page.extract_text() or ''
        except Exception:
            txt = ''
        n = len(ANCHOR_RX.findall(txt))
        if n:
            hits[i] = n
    return hits, len(reader.pages)


def to_ranges(pages, ctx=CTX, total=None):
    if not pages:
        return []
    cand = sorted(pages)
    ranges = []
    lo = hi = cand[0]
    for p in cand[1:]:
        if p - ctx <= hi + ctx + 1:
            hi = p
        else:
            ranges.append((max(1, lo - ctx), hi + ctx))
            lo = hi = p
    ranges.append((max(1, lo - ctx), hi + ctx))
    if total:
        ranges = [(a, min(b, total)) for a, b in ranges]
    return ranges


def covering_range(ranges):
    if not ranges:
        return None
    return (ranges[0][0], ranges[-1][1])


if __name__ == '__main__':
    import json
    out = {}
    for f in sys.argv[1:]:
        hits, total = scan(f)
        ranges = to_ranges(hits, total=total)
        cov = covering_range(ranges)
        out[Path(f).name] = {
            'pages': total, 'hit_pages': sorted(hits),
            'ranges': ranges, 'covering_range': cov,
            'pages_in_covering': (cov[1] - cov[0] + 1) if cov else 0,
        }
        print(Path(f).name, '| pages', total, '| hits',
              len(hits), '| ranges', len(ranges), '| covering', cov)
    Path('.work/prescan.json').write_text(
        json.dumps(out, indent=1), encoding='utf-8')
