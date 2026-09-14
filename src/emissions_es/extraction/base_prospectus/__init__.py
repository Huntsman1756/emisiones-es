"""BaseProspectusExtractor — folleto de base / doc. de registro.

El base prospectus aporta el marco (condiciones generales, placeholders);
los valores concretos llegan via final terms. Los placeholders
'[[ ] per cent.]' no son hechos — el extractor comparte los guards de
la maquinaria comun.
"""
from __future__ import annotations

import re

from emissions_es.extraction.final_terms import (FinalTermsExtractor,
                                               FIELD_SECTION)


BP_SECTIONS = {
    "interest": re.compile(
        r"tipo\s+de\s+inter[eé]s|interest|cup[oó]n|day\s+count|"
        r"base\s+de\s+c[aá]lculo|fixed\s+rate|floating\s+rate", re.I),
    "redemption": FinalTermsExtractor.section_patterns["redemption"],
    "exercise": FinalTermsExtractor.section_patterns["exercise"],
    "general": re.compile(
        r"programa|programme|emisores|issuers|divisa|currency|"
        r"denominaci[oó]n|form\s+of\s+final\s+terms", re.I),
    "structured": FinalTermsExtractor.section_patterns["structured"],
}


class BaseProspectusExtractor(FinalTermsExtractor):
    family_id = "base_prospectus"
    supported_roles = ("BASE_PROSPECTUS",)
    section_patterns = BP_SECTIONS
    field_sections = FIELD_SECTION
