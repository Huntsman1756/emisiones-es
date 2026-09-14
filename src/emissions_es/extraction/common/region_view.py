"""RegionView: vista acotada de un documento sobre los items de una
CandidateRegion. Reutiliza NormalizedDocumentView para geometria/provenance
pero restringe iter_text_blocks a la region localizada.
"""
from __future__ import annotations

from emissions_es.extraction.docview import NormalizedDocumentView


class RegionView(NormalizedDocumentView):
    def __init__(self, parent: NormalizedDocumentView, region):
        super().__init__(parent.doc, parent.source, parent.source_record_key,
                         parent.snapshot_sha256)
        self._items = list(region.items)

    def iter_text_blocks(self):
        yield from self._items
