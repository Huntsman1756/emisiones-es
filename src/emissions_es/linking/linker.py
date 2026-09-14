"""Orquestador del linker determinista.

Recorre el registry en orden de prioridad; la primera regla aplicable que
devuelve decision no-None gana. Si positivas y negativas coexisten dentro
de una regla ya lo resuelve la propia regla (AMBIGUOUS).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from emissions_es.linking.rules import (RULES, Candidate, KnowledgeBase,
                                        RuleOutput, SourceRecord)
from emissions_es.model import LinkDecision, RelationType


@dataclass
class LinkResult:
    source_record_key: str
    candidate: dict
    decision: LinkDecision
    relation: Optional[str] = None
    selected_target: Optional[dict] = None
    rule_id: str = ""
    rule_version: str = ""
    positive_evidence: list[str] = field(default_factory=list)
    negative_evidence: list[str] = field(default_factory=list)
    note: str = ""


def adjudicate(src: SourceRecord, cand: Candidate,
               kb: Optional[KnowledgeBase] = None) -> LinkResult:
    kb = kb or KnowledgeBase()
    for rule in RULES:
        if not rule.applies_to(src, cand):
            continue
        out: RuleOutput = rule.evaluate(src, cand, kb)
        if out.decision is None:
            continue
        return LinkResult(
            source_record_key=src.record_key,
            candidate={k: v for k, v in vars(cand).items() if v is not None},
            decision=out.decision,
            relation=out.relation.value if out.relation else None,
            selected_target=(
                {k: v for k, v in vars(cand).items() if v is not None}
                if out.decision == LinkDecision.EXACT_LINK else None),
            rule_id=rule.rule_id, rule_version=rule.version,
            positive_evidence=out.positive_evidence,
            negative_evidence=out.negative_evidence,
            note=out.note)
    raise AssertionError('NO_EVIDENCE_FALLBACK siempre decide')
