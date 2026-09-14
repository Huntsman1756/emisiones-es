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
    fecha: Optional[str] = None        # presentacion/fecha_registro DD/MM/YYYY


@dataclass
class Candidate:
    type: str                         # folleto | folleto_doc | security | admision_doc | ccff_doc | venue | none | unknown
    registro_oficial: Optional[str] = None
    isin: Optional[str] = None
    doc_url: Optional[str] = None
    record_key: Optional[str] = None
    rol: Optional[str] = None
    version: Optional[str] = None      # 'base' | 'supplement.k' | 'modification.k'


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
        self.adm_by_isin = {}
        for a in self.admisiones:
            if a.get('isin'):
                self.adm_by_isin.setdefault(a['isin'], []).append(a)

    def folleto_exists(self, reg: str) -> bool:
        return reg in self.fol_by_reg

    def folleto(self, reg: str):
        return self.fol_by_reg.get(reg)

    def folleto_version(self, reg: str, suffix: str):
        """Busca la observacion versionada: registro reg + sufijo '.k'/'-k'."""
        for f in self.folletos:
            if f.get('registro_oficial') == reg and \
                    f.get('version_suffix') == suffix:
                return f
        return None


def _d(s: str):
    """'DD/MM/YYYY' -> date; None si no parsea."""
    import datetime as _dt
    try:
        return _dt.datetime.strptime(s.strip(), '%d/%m/%Y').date()
    except Exception:
        return None


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
    if cand.registro_oficial is None:
        out.decision = LinkDecision.AMBIGUOUS
        out.negative_evidence.append(
            'candidato sin registro_oficial: nada que verificar')
        return out
    if cand.registro_oficial == src.numfol_link:
        # candidato versionado: solo el base vigente a fecha de la CCFF
        # puede definir sus terminos
        if cand.version and cand.version != 'base':
            kind, _, num = cand.version.partition('.')
            suf = ('.' if kind == 'supplement' else '-') + num
            fv = kb.folleto_version(cand.registro_oficial, suf)
            d_ccff, d_sup = _d(src.fecha or ''), _d(
                (fv or {}).get('fecha_registro', ''))
            if fv is None or d_ccff is None or d_sup is None:
                out.decision = LinkDecision.AMBIGUOUS
                out.negative_evidence.append(
                    f'version {cand.version} no verificable en corpus')
            elif d_sup > d_ccff:
                out.decision = LinkDecision.NO_LINK
                out.negative_evidence.append(
                    f'version {cand.version} ({d_sup}) postdata la CCFF '
                    f'({d_ccff}); no puede definir sus terminos')
            else:
                out.decision = LinkDecision.AMBIGUOUS
                out.negative_evidence.append(
                    f'version {cand.version} ({d_sup}) precede a la CCFF '
                    f'({d_ccff}); puede ser el documento vigente o no')
            return out
        out.positive_evidence.append(
            f'fila {src.record_key} enlaza explicitamente NUMFOL={src.numfol_link}')
        if cand.version == 'base' and kb.folleto_exists(cand.registro_oficial):
            # adjudicacion a nivel de documento-version: si ya existian
            # suplementos a fecha de la CCFF, la fila no resuelve que
            # version definio los terminos
            supps = [f for f in kb.folletos
                     if f.get('registro_oficial') == cand.registro_oficial
                     and (f.get('version_suffix') or '').startswith('.')]
            d_ccff = _d(src.fecha or '')
            earlier = [s for s in supps
                       if _d(s.get('fecha_registro', '')) and d_ccff
                       and _d(s['fecha_registro']) < d_ccff]
            if earlier:
                out.decision = LinkDecision.AMBIGUOUS
                out.negative_evidence.append(
                    f'{len(earlier)} suplemento(s) anteriores a la CCFF: '
                    'version vigente no resoluble desde la fila')
                return out
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
    if cand.type not in ('security', 'admission', 'admision_doc'):
        return out
    if not src.isin:
        out.decision = LinkDecision.AMBIGUOUS
        out.negative_evidence.append('fila de admision sin ISIN observable')
        return out
    # el ISIN de admision solo identifica el instrumento; nunca el documento
    if cand.type != 'security':
        sib = kb.adm_by_isin.get(src.isin, [])
        out.decision = LinkDecision.AMBIGUOUS
        if len(sib) > 1:
            out.negative_evidence.append(
                f'{len(sib)} admisiones comparten ISIN {src.isin}: la fila '
                'no identifica el documento')
        else:
            out.negative_evidence.append(
                'ISIN identifica el instrumento; no vincula la fila con '
                'un documento de admision concreto')
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
    """Fila SERIE de FTA: solo si la fila enlaza un documento propio hay
    relacion observable; en otro caso AMBIGUOUS."""
    out = RuleOutput(decision=None)
    if not (src.rol or '').startswith('SERIE'):
        return out
    if cand.type == 'none':
        out.decision = LinkDecision.NO_LINK
        out.negative_evidence.append('fila SERIE sin documento observable propio')
    elif cand.type == 'venue' and not src.doc_url:
        out.decision = LinkDecision.NO_LINK
        out.negative_evidence.append('serie marcada sin admision')
    elif cand.type == 'folleto':
        if cand.registro_oficial != src.registro_oficial:
            out.decision = LinkDecision.NO_LINK
            out.negative_evidence.append(
                f'serie de {src.registro_oficial} emparejada con folleto '
                f'{cand.registro_oficial}')
        elif src.doc_url:
            out.decision = LinkDecision.EXACT_LINK
            out.relation = RelationType.DEFINES_TERMS_FOR
            out.positive_evidence.append(
                'la fila de serie enlaza un documento propio')
        else:
            out.decision = LinkDecision.AMBIGUOUS
            out.negative_evidence.append(
                'fila de serie sin documento propio: el base del fondo no '
                'es documento de la serie')
    return out


def _r_programme_succession(src, cand, kb):
    """Sucesion anual de programa: mismo emisor/rol con registro distinto.
    La fila CNMV no expone ningun campo de sucesion: registro consecutivo
    en el tiempo no es evidencia de REPLACES -> AMBIGUOUS."""
    out = RuleOutput(decision=None)
    if src.family != 'cnmv_folletos_emision' or cand.type != 'folleto':
        return out
    if src.rol not in ('PROGRAMA RENTA FIJA', 'DOC. REGISTRO UNIVERSAL',
                       'DOC. REGISTRO'):
        return out
    prev = kb.folleto(cand.registro_oficial)
    if prev is None:
        out.decision = LinkDecision.AMBIGUOUS
        out.negative_evidence.append('candidato no observable en corpus')
        return out
    if prev.get('emisor') != src.emisor:
        out.negative_evidence.append('emisor distinto')
        out.decision = LinkDecision.NO_LINK
    elif cand.registro_oficial == src.registro_oficial or \
            prev.get('rol') != src.rol:
        out.decision = LinkDecision.AMBIGUOUS
        out.negative_evidence.append(
            'mismo emisor pero sin evidencia de sucesion')
    else:
        out.decision = LinkDecision.AMBIGUOUS
        out.negative_evidence.append(
            f'mismo emisor ({src.emisor}) y rol; {cand.registro_oficial} '
            'precede en el tiempo, pero la fila no declara sucesion')
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
    LinkRule('CNMV_CCFF_EXPLICIT_NUMFOL', '1.1',
             'CCFF enlaza su folleto via NUMFOL explicito en la fila',
             lambda s, c: s.family == 'cnmv_ccff', _r_ccff_explicit_numfol),
    LinkRule('CNMV_SUPPLEMENT_SUFFIX', '1.0',
             'registro X.k con rol SUPLEMENTO -> base X',
             lambda s, c: (s.rol or '').startswith('SUPLEMENTO'), _r_supplement_suffix),
    LinkRule('CNMV_MODIFICATION_DASH', '1.0',
             'registro X-k con rol MODIFICACION -> corrigido X',
             lambda s, c: 'MODIFICACI' in (s.rol or '').upper(), _r_modification_dash),
    LinkRule('CNMV_ADMISSION_ISIN', '1.1',
             'admision -> security por ISIN exacto',
             lambda s, c: s.family == 'cnmv_admision', _r_admission_isin),
    LinkRule('CNMV_SERIE_NO_DOC', '1.1',
             'serie FTA sin doc propio -> sin enlace doc-doc',
             lambda s, c: (s.rol or '').startswith('SERIE'), _r_serie_no_doc),
    LinkRule('CNMV_PROGRAMME_SUCCESSION', '1.1',
             'mismo emisor/rol, registro distinto sin sucesion declarada '
             '-> AMBIGUOUS',
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
