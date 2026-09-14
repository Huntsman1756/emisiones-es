"""SecuritiesNoteExtractor — nota sobre los valores (superficie admision).

Misma mecanica que FinalTermsExtractor con secciones ajustadas al layout
de notas de valores (X28-pattern: instrumento admitido, condiciones).
"""
from __future__ import annotations

import re

from emissions_es.extraction.final_terms import (FinalTermsExtractor,
                                               FIELD_SECTION)


SN_SECTIONS = {
    "interest": FinalTermsExtractor.section_patterns["interest"],
    "redemption": FinalTermsExtractor.section_patterns["redemption"],
    "exercise": FinalTermsExtractor.section_patterns["exercise"],
    "general": re.compile(
        r"\bisin\b|divisa|currency|denominaci[oó]n|importe\s+nominal|"
        r"admisi[oó]n|admission|descripci[oó]n\s+de\s+los\s+valores", re.I),
    "structured": FinalTermsExtractor.section_patterns["structured"],
}


class SecuritiesNoteExtractor(FinalTermsExtractor):
    family_id = "securities_note"
    supported_roles = ("SECURITIES_NOTE",)
    section_patterns = SN_SECTIONS
    field_sections = FIELD_SECTION
