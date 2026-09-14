"""Linker G1 — family-first (PORT_PATTERN: edgartools ShelfLifecycle).

    1. explicit family      familia demostrada por identificador estable
                            (NUMFOL en fila, sufijo .k/-k, referencia
                            explicita en documento) — nunca por fecha.
    2. candidate family     familia del candidato por la misma regla.
    3. role compatibility   rol origen vs rol candidato.
    4. explicit relation    SUPPLEMENTS/MODIFIES/DEFINES_TERMS_FOR...
    5. lifecycle placement  el tiempo SOLO ordena dentro de familia ya
                            demostrada.

Salidas operacionales G1:
    AUTO_LINKED       evidencia suficiente y verificable
    REVIEW_REQUIRED   relacion plausible pero no demostrable
    NO_LINK           sin relacion o evidencia negativa

Safety: false AUTO_LINKED = 0, forced ambiguous = 0. Ante la duda:
REVIEW_REQUIRED, nunca AUTO_LINKED.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from emissions_es.linking.rules import (Candidate, KnowledgeBase,
                                        SourceRecord)
from emissions_es.linking.linker import adjudicate
from emissions_es.model import LinkDecision


class OpDecision(str, Enum):
    AUTO_LINKED = "AUTO_LINKED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_LINK = "NO_LINK"


@dataclass
class OpResult:
    source_record_key: str
    decision: OpDecision
    relation: Optional[str] = None
    target_family: Optional[str] = None
    source_family: Optional[str] = None
    rule_id: str = ""
    positive_evidence: list[str] = field(default_factory=list)
    negative_evidence: list[str] = field(default_factory=list)
    note: str = ""


def family_key_of(record_key: str, reg: Optional[str],
                  surface: Optional[str]) -> Optional[str]:
    """Familia desde evidencia estructural; nunca temporal."""
    import re
    if surface == "cnmv_admision" or (record_key or "").startswith("ADM_"):
        return f"ISSUE_ADM_{reg}" if reg else None
    base = (reg or "").split(".")[0].split("-")[0]
    return f"PROG_{base}" if base else None


def link(source: SourceRecord, cand: Candidate,
         kb: Optional[KnowledgeBase] = None) -> OpResult:
    """Traduce el adjudicador estructural a semantica operacional G1."""
    kb = kb or KnowledgeBase()
    r = adjudicate(source, cand, kb)

    src_fam = family_key_of(source.record_key, source.registro_oficial,
                            source.family)
    cand_fam = family_key_of(
        cand.record_key or cand.registro_oficial or "",
        cand.registro_oficial, None)

    if r.decision == LinkDecision.EXACT_LINK:
        # AUTO_LINKED exige familia explicita o identidad exacta
        # (ISIN de instrumento). Nunca promovida por proximidad.
        return OpResult(
            source_record_key=source.record_key,
            decision=OpDecision.AUTO_LINKED, relation=r.relation,
            source_family=src_fam, target_family=cand_fam,
            rule_id=r.rule_id,
            positive_evidence=r.positive_evidence + ["familia/identidad explicita"],
            negative_evidence=r.negative_evidence, note=r.note)

    if r.decision == LinkDecision.NO_LINK:
        return OpResult(source_record_key=source.record_key,
                        decision=OpDecision.NO_LINK, source_family=src_fam,
                        target_family=cand_fam, rule_id=r.rule_id,
                        negative_evidence=r.negative_evidence, note=r.note)

    # AMBIGUOUS estructural -> REVIEW_REQUIRED (nunca auto-link)
    return OpResult(source_record_key=source.record_key,
                    decision=OpDecision.REVIEW_REQUIRED,
                    source_family=src_fam, target_family=cand_fam,
                    rule_id=r.rule_id, positive_evidence=r.positive_evidence,
                    negative_evidence=r.negative_evidence or
                    ["relacion plausible pero no demostrable"],
                    note=r.note)
