"""Interfaz comun de extractor por familia (PORT_PATTERN: vc-statement-parser
Extractor interface + plugin registry).

    supports(classification) -> bool
    locate(view)             -> regiones candidatas
    extract(view, regions)   -> dict[field, ExtractionResult]
    verify(observation)      -> verbatim check sobre evidencia

Cada familia hereda y registra sus secciones/campos; nunca un
mega-extractor universal.
"""
from __future__ import annotations

import re
from typing import Optional

from emissions_es.extraction.common.result import ExtractionResult, FailureClass
from emissions_es.extraction.common.locate import (grep_first_scan,
                                                   locate_regions)
from emissions_es.model import FactStatus, TermObservation


class FamilyExtractor:
    family_id: str = "base"
    version: str = "1.0"
    supported_roles: tuple = ()
    # section -> regex de lexemas que la delimitan (baratos)
    section_patterns: dict = {}
    # campo -> nombre de seccion donde debe buscarse
    field_sections: dict = {}

    def supports(self, classification) -> bool:
        return classification.document_role in self.supported_roles

    def locate(self, view) -> dict:
        hits = grep_first_scan(view, self.section_patterns)
        return {s: locate_regions(view, s, hits)
                for s in self.section_patterns}

    def extract(self, view, regions: dict) -> dict:
        raise NotImplementedError

    def verify(self, view, obs: TermObservation) -> TermObservation:
        """Verbatim verification: el lexema debe existir en la evidencia o
        en el texto fuente del bloque citado."""
        from emissions_es.verification.verbatim import verify_observation
        return verify_observation(view, obs)

    def post_process(self, view, out: dict) -> dict:
        return out

    def run(self, view, classification) -> dict:
        regions = self.locate(view)
        out = self.extract(view, regions)
        out = self.post_process(view, out)
        for field, res in out.items():
            if (res.observation is not None
                    and res.observation.status in (FactStatus.OBSERVED,
                                                   FactStatus.DERIVED)):
                res.observation = self.verify(view, res.observation)
        return out
