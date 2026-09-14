"""IssueDocumentExtractor — documentos de emision standalone (ISSUE_DOC).

Cobertura minima G1: campos core (isin, importe, fechas, cupon) sin
semantica de programa; aplicable cuando el documento es unico y
autocontenido (p.ej. emisiones sin folleto de base separado).
"""
from __future__ import annotations

import re

from emissions_es.extraction.final_terms import (FinalTermsExtractor,
                                               FIELD_SECTION)


ID_SECTIONS = {
    "interest": FinalTermsExtractor.section_patterns["interest"],
    "redemption": FinalTermsExtractor.section_patterns["redemption"],
    "exercise": FinalTermsExtractor.section_patterns["exercise"],
    "general": re.compile(
        r"\bisin\b|divisa|currency|denominaci[oó]n|importe\s+nominal|"
        r"emisi[oó]n|issue", re.I),
    "structured": FinalTermsExtractor.section_patterns["structured"],
}


class IssueDocumentExtractor(FinalTermsExtractor):
    family_id = "issue_doc"
    supported_roles = ("ISSUE_DOC",)
    section_patterns = ID_SECTIONS
    field_sections = FIELD_SECTION
