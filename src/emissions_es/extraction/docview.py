"""NormalizedDocumentView: adaptador fino sobre DoclingDocument.

No duplica el modelo documental de Docling: itera sus items y traduce su
provenance (page_no/bbox/charspan) a EvidencePointer del proyecto.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

from emissions_es.model import EvidencePointer


def prov_to_evidence(item, source: str, source_record_key: str,
                     snapshot_sha256: Optional[str] = None,
                     extractor: str = 'docling') -> Optional[EvidencePointer]:
    """Docling ProvenanceItem -> EvidencePointer."""
    prov = getattr(item, 'prov', None) or []
    if not prov:
        return None
    p = prov[0]
    bbox = None
    if getattr(p, 'bbox', None) is not None:
        b = p.bbox
        bbox = (round(b.l, 2), round(b.t, 2), round(b.r, 2), round(b.b, 2))
    cs = getattr(p, 'charspan', None)
    return EvidencePointer(
        source=source, source_record_key=source_record_key,
        snapshot_sha256=snapshot_sha256,
        page=getattr(p, 'page_no', None),
        bbox=bbox,
        charspan=tuple(cs) if cs else None,
        text_excerpt=(getattr(item, 'text', None) or '')[:300],
        extractor=extractor)


class TableView:
    def __init__(self, table_item):
        self.item = table_item
        self.grid = table_item.data.grid  # rows of TableCell

    def rows_text(self) -> list[list[str]]:
        return [[(c.text or '').strip() for c in row] for row in self.grid]

    def cell(self, r: int, c: int) -> str:
        try:
            return (self.grid[r][c].text or '').strip()
        except IndexError:
            return ''


class NormalizedDocumentView:
    def __init__(self, doc, source: str, source_record_key: str,
                 snapshot_sha256: Optional[str] = None):
        self.doc = doc                       # DoclingDocument (referencia)
        self.source = source
        self.source_record_key = source_record_key
        self.snapshot_sha256 = snapshot_sha256

    def iter_text_blocks(self) -> Iterable:
        for t in self.doc.texts:
            yield t

    def iter_tables(self) -> Iterable[TableView]:
        for t in self.doc.tables:
            yield TableView(t)

    def iter_key_values(self) -> Iterable:
        for kv in getattr(self.doc, 'key_value_items', []) or []:
            yield kv

    def find_items(self, pattern: str, flags=re.I) -> list:
        rx = re.compile(pattern, flags)
        return [t for t in self.doc.texts if rx.search(getattr(t, 'text', '') or '')]

    def find_tables_with(self, pattern: str, flags=re.I) -> list[TableView]:
        rx = re.compile(pattern, flags)
        out = []
        for tv in self.iter_tables():
            if any(rx.search(c) for row in tv.rows_text() for c in row):
                out.append(tv)
        return out

    def text(self) -> str:
        return '\n'.join(getattr(t, 'text', '') or '' for t in self.doc.texts)

    def evidence_for(self, item, extractor: str) -> Optional[EvidencePointer]:
        return prov_to_evidence(item, self.source, self.source_record_key,
                                self.snapshot_sha256, extractor)

    def page_of(self, item) -> Optional[int]:
        prov = getattr(item, 'prov', None) or []
        return getattr(prov[0], 'page_no', None) if prov else None

    def _bbox(self, item):
        prov = getattr(item, 'prov', None) or []
        if prov and getattr(prov[0], 'bbox', None) is not None:
            return prov[0].page_no, prov[0].bbox
        return None, None

    def value_right_of(self, label_item, max_dy: float = 6.0):
        """Layout columnar: etiqueta en item sin valor -> item a la
        derecha en la misma linea visual (misma pagina, solape vertical,
        x_left > x_right del label). Devuelve el item candidato o None."""
        page, lb = self._bbox(label_item)
        if lb is None:
            return None
        cy = (lb.t + lb.b) / 2
        best, best_dx = None, None
        for t in self.doc.texts:
            if t is label_item:
                continue
            tp, tb = self._bbox(t)
            if tb is None or tp != page:
                continue
            tcy = (tb.t + tb.b) / 2
            if abs(tcy - cy) > max_dy or tb.l < lb.r - 2:
                continue
            txt = (getattr(t, 'text', '') or '').strip()
            if not txt:
                continue
            dx = tb.l - lb.r
            if best_dx is None or dx < best_dx:
                best, best_dx = t, dx
        return best

    def label_below(self, item, max_dy: float = 30.0):
        """Subfila inmediatamente debajo (misma pagina, siguiente linea)."""
        page, lb = self._bbox(item)
        if lb is None:
            return None
        best, best_dy = None, None
        for t in self.doc.texts:
            if t is item:
                continue
            tp, tb = self._bbox(t)
            if tb is None or tp != page:
                continue
            # BOTTOMLEFT: t mayor = mas arriba; debajo = tb.t < lb.t
            dy = lb.t - tb.t
            if 0 < dy <= max_dy and abs(tb.l - lb.l) < 120:
                if best_dy is None or dy < best_dy:
                    best, best_dy = t, dy
        return best
