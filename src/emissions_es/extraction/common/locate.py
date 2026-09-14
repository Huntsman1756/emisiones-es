"""Locate-then-extract: separacion LOCATION de PARSING.

Patron (PORT_PATTERN): sovereign-prospectus-corpus clause_extractor —
grep_first_scan -> identify_clause_sections (density clustering) ->
extract verbatim region -> verify_extraction.

Aqui el primer scan recorre bloques Docling (o texto plano) con regex
baratos por seccion; las coincidencias se agrupan por pagina y se devuelven
regiones candidatas acotadas (ventana de items/paginas), nunca el documento
entero.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional


@dataclass
class CandidateRegion:
    region_id: str
    section: str
    pages: list[int] = field(default_factory=list)
    items: list = field(default_factory=list)      # Docling items
    score: float = 0.0


def grep_first_scan(view, section_patterns: dict[str, re.Pattern]) -> dict:
    """section -> [items que contienen un lexema de la seccion]."""
    hits: dict[str, list] = {s: [] for s in section_patterns}
    for t in view.iter_text_blocks():
        txt = getattr(t, "text", "") or ""
        for s, rx in section_patterns.items():
            if rx.search(txt):
                hits[s].append(t)
    # tambien en celdas de tabla
    for tv in view.iter_tables():
        for row in tv.rows_text():
            for c in row:
                for s, rx in section_patterns.items():
                    if c and rx.search(c):
                        hits[s].append(tv.item)
    return hits


def locate_regions(view, section: str, hits: dict, window: int = 40
                   ) -> list[CandidateRegion]:
    """Clustering por pagina: cada pagina con hits genera una region que
    incluye sus items mas los `window` items adyacentes en orden doc."""
    items = hits.get(section) or []
    if not items:
        return []
    all_items = list(view.iter_text_blocks())
    index = {id(t): i for i, t in enumerate(all_items)}
    pages = sorted({view.page_of(t) or -1 for t in items})
    regions = []
    for pg in pages:
        core = [t for t in items if (view.page_of(t) or -1) == pg]
        idxs = [index.get(id(t)) for t in core if index.get(id(t)) is not None]
        if idxs:
            lo, hi = max(0, min(idxs) - window // 4), min(
                len(all_items), max(idxs) + window)
            region_items = all_items[lo:hi]
        else:
            region_items = core
        regions.append(CandidateRegion(
            region_id=f"{section}@p{pg}", section=section, pages=[pg],
            items=region_items, score=float(len(core))))
    return regions
