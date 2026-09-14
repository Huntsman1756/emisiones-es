"""Extractor dispatcher: classification -> FamilyExtractor -> results.

    SourceDocument -> classify() -> DocumentClassification
                   -> registry.supports() -> FamilyExtractor.run()

UNKNOWN o rol sin extractor registrado -> {} con nota, nunca best-guess.
"""
from __future__ import annotations

from emissions_es.extraction.base_prospectus import BaseProspectusExtractor
from emissions_es.extraction.final_terms import FinalTermsExtractor
from emissions_es.extraction.issue_doc import IssueDocumentExtractor
from emissions_es.extraction.securities_note import SecuritiesNoteExtractor

REGISTRY = [
    FinalTermsExtractor(),
    SecuritiesNoteExtractor(),
    IssueDocumentExtractor(),
    BaseProspectusExtractor(),
]


def extractor_for(classification):
    for ex in REGISTRY:
        if ex.supports(classification):
            return ex
    return None


def extract_document(view, classification) -> dict:
    ex = extractor_for(classification)
    if ex is None:
        return {"_note": f"no extractor for role {classification.document_role}"}
    return ex.run(view, classification)
