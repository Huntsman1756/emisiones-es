"""Linker determinista: adjudicacion de enlaces documento<->documento /
documento<->security a partir de evidencia estructural observable.

Diseno:
- Cada regla es un objeto registrado con rule_id/version; decide sobre un
  par (source_record, candidate) usando el knowledge base de observaciones.
- Senales positivas Y negativas. Un candidato con ambas -> AMBIGUOUS.
- Ninguna regla genera enlace factual por coincidencia de prefijo:
  la evidencia debe venir de la fila (p.ej. enlace NUMFOL explicito)
  o de un identificador cualificado exacto (ISIN).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from emissions_es.model import LinkDecision, RelationType


@dataclass
class SourceRecord:
    """Vista minima de una fila fuente para el linker."""
    family: str                       # cnmv_ccff | cnmv_folletos_emision | cnmv_admision | portfolio_exchange
    record_key: str
    registro_oficial: Optional[str] = None
    version_suffix: Optional[str] = None
    rol: Optional[str] = None
    isin: Optional[str] = None
    doc_url: Optional[str] = None
    numfol_link: Optional[str] = None  # NUMFOL explicito observado en la fila
    emisor: Optional[str] = None


@dataclass
class Candidate:
    type: str                         # folleto | folleto_doc | security | admision_doc | ccff_doc | venue | none | unknown
    registro_oficial: Optional[str] = None
    isin: Optional[str] = None
    doc_url: Optional[str] = None
    record_key: Optional[str] = None
    rol: Optional[str] = None


@dataclass
class RuleOutput:
    decision: Optional[LinkDecision]   # None = la regla no aplica
    relation: Optional[RelationType] = None
    positive_evidence: list[str] = field(default_factory=list)
    negative_evidence: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class LinkRule:
    rule_id: str
    version: str
    description: str
    applies_to: callable
    evaluate: callable               # (SourceRecord, Candidate, KB) -> RuleOutput


class KnowledgeBase:
    """Observaciones adquiridas; permite verificar que un candidato existe
    y que la evidencia estructural de la fila es la esperada."""

    def __init__(self, folletos=(), ccff=(), admisiones=()):
        self.fol_by_reg = {f['registro_oficial']: f for f in folletos}
        self.folletos = list(folletos)
        self.ccff = list(ccff)
        self.admisiones = list(admisiones)

    def folleto_exists(self, reg: str) -> bool:
        return reg in self.fol_by_reg

    def folleto(self, reg: str):
        return self.fol_by_reg.get(reg)


# ---------- reglas ----------

def _r_ccff_explicit_numfol(src, cand, kb):
    """CCFF -> folleto/programa. La fila CCFF contiene enlace explicito
    folletosemisionopv?NUMFOL=X hacia su folleto base."""
    out = RuleOutput(decision=None)
    if src.family != 'cnmv_ccff' or cand.type not in ('folleto',):
        return out
    if src.numfol_link is None:
        out.decision = LinkDecision.AMBIGUOUS
        out.negative_evidence.append('fila CCFF sin enlace NUMFOL observable')
        return out
    if cand.registro_oficial == src.numfol_link:
        out.positive_evidence.append(
            f'fila {src.record_key} enlaza explicitamente NUMFOL={src.numfol_link}')
        if kb.folleto_exists(cand.registro_oficial):
            out.positive_evidence.append('registro destino existe en corpus observado')
        out.decision = LinkDecision.EXACT_LINK
        out.relation = RelationType.DEFINES_TERMS_FOR
    else:
        out.negative_evidence.append(
            f'fila enlaza NUMFOL={src.numfol_link} pero candidato es {cand.registro_oficial}')
        out.decision = LinkDecision.NO_LINK
    return out


def _r_supplement_suffix(src, cand, kb):
    """Folleto con sufijo .k y rol SUPLEMENTO -> folleto base X."""
    out = RuleOutput(decision=None)
    if src.family != 'cnmv_folletos_emision':
        return out
    if not (src.rol or '').startswith('SUPLEMENTO'):
        return out
    if cand.type != 'folleto':
        return out
    if not src.version_suffix:
        out.decision = LinkDecision.AMBIGUOUS
        out.negative_evidence.append('rol SUPLEMENTO sin sufijo de version observable')
        return out
    if cand.registro_oficial == src.registro_oficial:
        out.positive_evidence.append(
            f'registro {src.registro_oficial}{src.version_suffix} referencia al base {src.registro_oficial}')
        out.decision = LinkDecision.EXACT_LINK
        out.relation = RelationType.SUPPLEMENTS
    else:
        out.negative_evidence.append(
            f'suplemento de {src.registro_oficial} emparejado con {cand.registro_oficial}')
        out.decision = LinkDecision.NO_LINK
    return out


def _r_modification_dash(src, cand, kb):
    """Folleto con sufijo -k y rol MODIFICACION -> documento corregido X."""
    out = RuleOutput(decision=None)
    if src.family != 'cnmv_folletos_emision':
        return out
    if 'MODIFICACI' not in (src.rol or '').upper():
        return out
    if cand.type != 'folleto':
        return out
    if cand.registro_oficial == src.registro_oficial:
        out.positive_evidence.append(
            f'modificacion {src.record_key} del folleto {src.registro_oficial}')
        out.decision = LinkDecision.EXACT_LINK
        out.relation = RelationType.CORRECTS
    else:
        out.negative_evidence.append(
            f'modificacion de {src.emisor} ({src.registro_oficial}) emparejada con '
            f'folleto ajeno {cand.registro_oficial}')
        out.decision = LinkDecision.NO_LINK
    return out


def _r_admission_isin(src, cand, kb):
    """Admision -> security via ISIN exacto cualificado."""
    out = RuleOutput(decision=None)
    if src.family != 'cnmv_admision':
        return out
    if cand.type != 'security':
        return out
    if not src.isin:
        out.decision = LinkDecision.AMBIGUOUS
        out.negative_evidence.append('fila de admision sin ISIN observable')
        return out
    if cand.isin == src.isin:
        out.positive_evidence.append(f'ISIN exacto {src.isin} en fila de admision')
        out.decision = LinkDecision.EXACT_LINK
        out.relation = RelationType.ADMISSION_OF
    else:
        out.negative_evidence.append(f'ISIN {cand.isin} != {src.isin}')
        out.decision = LinkDecision.NO_LINK
    return out


def _r_serie_no_doc(src, cand, kb):
    """Fila SERIE de FTA sin documento propio: no hay doc-doc observable."""
    out = RuleOutput(decision=None)
    if not (src.rol or '').startswith('SERIE'):
        return out
    if cand.type == 'none':
        out.decision = LinkDecision.NO_LINK
        out.negative_evidence.append('fila SERIE sin documento observable propio')
    elif cand.type == 'venue' and not src.doc_url:
        out.decision = LinkDecision.NO_LINK
        out.negative_evidence.append('serie marcada sin admision')
    return out


def _r_programme_succession(src, cand, kb):
    """Sucesion anual de programa: mismo emisor, mismo rol, registro
    consecutivo en el tiempo -> REPLACES (renovacion, no redeposito)."""
    out = RuleOutput(decision=None)
    if src.family != 'cnmv_folletos_emision' or cand.type != 'folleto':
        return out
    if src.rol not in ('PROGRAMA RENTA FIJA', 'DOC. REGISTRO UNIVERSAL', 'DOC. REGISTRO'):
        return out
    prev = kb.folleto(cand.registro_oficial)
    if prev is None:
        out.decision = LinkDecision.AMBIGUOUS
        out.negative_evidence.append('candidato no observable en corpus')
        return out
    if prev.get('emisor') == src.emisor and prev.get('rol') == src.rol and \
            cand.registro_oficial != src.registro_oficial:
        out.positive_evidence.append(
            f'mismo emisor ({src.emisor}) y rol ({src.rol}); '
            f'{cand.registro_oficial} precede a {src.registro_oficial}')
        out.decision = LinkDecision.EXACT_LINK
        out.relation = RelationType.REPLACES
    elif prev.get('emisor') != src.emisor:
        out.negative_evidence.append('emisor distinto')
        out.decision = LinkDecision.NO_LINK
    else:
        out.decision = LinkDecision.AMBIGUOUS
        out.note = 'mismo emisor pero sucesion temporal no verificable'
    return out


def _r_portfolio_doc(src, cand, kb):
    """Documento Portfolio -> security via ISIN en ficha de instrumento."""
    out = RuleOutput(decision=None)
    if src.family != 'portfolio_exchange':
        return out
    if cand.type == 'security' and src.isin and cand.isin == src.isin:
        out.positive_evidence.append(
            'ficha de instrumento portfolio.exchange lista el documento con ISIN')
        out.decision = LinkDecision.EXACT_LINK
        out.relation = RelationType.DEFINES_TERMS_FOR
    return out


def _r_generic_no_evidence(src, cand, kb):
    """Nada aplica: candidato sin evidencia estructural -> AMBIGUOUS.
    Nunca promueve por plausibilidad."""
    out = RuleOutput(decision=LinkDecision.AMBIGUOUS,
                     note='ninguna regla aporto evidencia suficiente')
    if cand.type == 'none':
        out.decision = LinkDecision.NO_LINK
        out.negative_evidence.append('sin candidato propuesto')
    return out


RULES: list[LinkRule] = [
    LinkRule('CNMV_CCFF_EXPLICIT_NUMFOL', '1.0',
             'CCFF enlaza su folleto via NUMFOL explicito en la fila',
             lambda s, c: s.family == 'cnmv_ccff', _r_ccff_explicit_numfol),
    LinkRule('CNMV_SUPPLEMENT_SUFFIX', '1.0',
             'registro X.k con rol SUPLEMENTO -> base X',
             lambda s, c: (s.rol or '').startswith('SUPLEMENTO'), _r_supplement_suffix),
    LinkRule('CNMV_MODIFICATION_DASH', '1.0',
             'registro X-k con rol MODIFICACION -> corrigido X',
             lambda s, c: 'MODIFICACI' in (s.rol or '').upper(), _r_modification_dash),
    LinkRule('CNMV_ADMISSION_ISIN', '1.0',
             'admision -> security por ISIN exacto',
             lambda s, c: s.family == 'cnmv_admision', _r_admission_isin),
    LinkRule('CNMV_SERIE_NO_DOC', '1.0',
             'serie FTA sin doc propio -> sin enlace doc-doc',
             lambda s, c: (s.rol or '').startswith('SERIE'), _r_serie_no_doc),
    LinkRule('CNMV_PROGRAMME_SUCCESSION', '1.0',
             'mismo emisor/rol, registro consecutivo -> REPLACES',
             lambda s, c: (s.rol or '') in
             ('PROGRAMA RENTA FIJA', 'DOC. REGISTRO UNIVERSAL', 'DOC. REGISTRO'),
             _r_programme_succession),
    LinkRule('PSE_INSTRUMENT_DOC', '1.0',
             'documento Portfolio -> security por ISIN de ficha',
             lambda s, c: s.family == 'portfolio_exchange', _r_portfolio_doc),
    LinkRule('NO_EVIDENCE_FALLBACK', '1.0',
             'sin evidencia estructural -> AMBIGUOUS/NO_LINK',
             lambda s, c: True, _r_generic_no_evidence),
]
