"""Verbatim verification (PORT_PATTERN: sovereign-prospectus-corpus
verify_extraction — exact_quote in raw_text, whitespace-normalized).

Regla: antes de promover OBSERVED/DERIVED, el raw_lexeme debe existir en
el texto fuente del documento (bloque citado o, en su defecto, el texto
completo de la vista). Un valor normalizado correcto cuya evidencia no se
verifica queda VALUE_UNVERIFIED — nunca OBSERVED.
"""
from __future__ import annotations

import re
from typing import Optional

from emissions_es.model import FactStatus, TermObservation

_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS.sub(" ", s or "").strip().lower()


def _lexeme_in_view(view, lexeme: str) -> bool:
    target = _norm(lexeme)
    if not target:
        return False
    for t in view.iter_text_blocks():
        if target in _norm(getattr(t, "text", "") or ""):
            return True
    for tv in view.iter_tables():
        for row in tv.rows_text():
            for c in row:
                if c and target in _norm(c):
                    return True
    return False


def _verify_evidence_excerpts(view, obs: TermObservation) -> bool:
    """Cada excerpt de evidencia debe existir verbatim en la vista."""
    evs = [e for e in (obs.evidence or []) if (e.text_excerpt or "").strip()]
    if not evs:
        return False
    return all(_lexeme_in_view(view, e.text_excerpt) for e in evs)


def verify_observation(view, obs: TermObservation) -> TermObservation:
    """Verifica la evidencia verbatim. Muta y devuelve la observacion."""
    if isinstance(obs.value, list):
        # observacion multi-valor: cada elemento se apoya en un excerpt
        # de evidencia; todos deben verificarse verbatim en el documento
        if _verify_evidence_excerpts(view, obs):
            obs.confidence_class = "verified_verbatim"
        else:
            obs.confidence_class = "VALUE_UNVERIFIED"
            obs.status = FactStatus.OBSERVED
            obs.value = None
        return obs
    lex = (obs.raw_lexeme or "").strip()
    if not lex:
        obs.confidence_class = "no_lexeme"
        return obs
    # 1. verbatim dentro del excerpt ya capturado
    for ev in obs.evidence or []:
        if _norm(lex) in _norm(ev.text_excerpt or ""):
            obs.confidence_class = "verified_verbatim"
            return obs
    # 2. verbatim en cualquier bloque/celda del documento fuente
    if _lexeme_in_view(view, lex):
        obs.confidence_class = "verified_verbatim_doclevel"
        return obs
    obs.confidence_class = "VALUE_UNVERIFIED"
    obs.status = FactStatus.OBSERVED   # evidencia existe pero sin valor verificable
    obs.value = None
    return obs
