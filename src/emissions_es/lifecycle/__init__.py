"""Lifecycle relations — pipeline separado del contractual extraction.

Relaciones gate-eligible G1: SUPPLEMENTS, MODIFIES.
CORRECTS / REPLACES / REDEPOSIT: INSUFFICIENT_EVIDENCE en el corpus
adquirido; no se fabrican reglas sin material.

Patron (PORT_PATTERN): edgartools ShelfLifecycle — la familia se
establece por identificador estable; el tiempo solo ordena dentro de
familia demostrada.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class LifecycleRelation(str, Enum):
    SUPPLEMENTS = "SUPPLEMENTS"
    MODIFIES = "MODIFIES"
    CORRECTS = "CORRECTS"        # INSUFFICIENT_EVIDENCE en corpus G1
    REPLACES = "REPLACES"        # idem
    REDEPOSIT = "REDEPOSIT"      # idem


@dataclass
class LifecycleEdge:
    from_key: str
    to_key: str
    relation: LifecycleRelation
    evidence: str
    provable: bool = True


def infer_relation(doc_reg: str, doc_kind: str,
                   target_reg: str) -> Optional[LifecycleEdge]:
    """doc 'X.k' SUPLEMENTO -> SUPPLEMENTS X; 'X-k' MODIFICACION ->
    MODIFIES X. Solo si la evidencia estructural lo soporta."""
    base = doc_reg.split(".")[0].split("-")[0]
    kind = (doc_kind or "").upper()
    if target_reg != base:
        return None
    if "SUPLEMENTO" in kind or re.search(r"\.\d+$", doc_reg):
        return LifecycleEdge(doc_reg, target_reg, LifecycleRelation.SUPPLEMENTS,
                             f"{doc_reg} listado como SUPLEMENTO de {base}")
    if "MODIFICACI" in kind or re.search(r"-\d+$", doc_reg):
        return LifecycleEdge(doc_reg, target_reg, LifecycleRelation.MODIFIES,
                             f"{doc_reg} listado como MODIFICACION de {base}")
    return None
