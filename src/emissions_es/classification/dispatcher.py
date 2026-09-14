"""Family/role dispatcher G1 — cascada de senales auditable.

Patron (PORT_PATTERN): vc-statement-parser dispatcher (header signatures +
required data anchors + UNKNOWN fallback) y cascada _424b_classifier de
edgartools (prior estructural -> texto acotado -> senales -> unknown).

Jerarquia de senales (de mas fuerte a mas debil):
  1. structured source metadata   (acquisition_surface, tipo_valor, sufijo)
  2. explicit title/header        (primera pagina, acotado)
  3. required data anchors        (bloques de datos obligatorios del rol)
  4. document-specific signatures (lexemas distintivos acotados)
  5. layout/section signals
  6. UNKNOWN

Regla dura: una mencion nunca clasifica; UNKNOWN -> REVIEW_REQUIRED.
Toda senal usada queda registrada en `signals` para auditoria.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

HEADER_WINDOW = 4000   # chars iniciales donde se buscan titulos


@dataclass
class SourceDocument:
    """Lo minimo que el dispatcher necesita: registro fuente + texto
    acotado del documento (o None si solo hay metadatos)."""
    source_record_key: str
    acquisition_surface: str           # CNMV_CCFF | CNMV_FOLLETOS_EMISION |
                                       # CNMV_ADMISSION | CNMV_FOLLETO_DETAIL | ...
    registro_oficial: Optional[str] = None
    numfol: Optional[str] = None
    issuer_key: Optional[str] = None
    head_text: str = ""                # ~primeras paginas; puede estar vacio
    source_meta: dict = field(default_factory=dict)   # rol, denominacion, ...


@dataclass
class DocumentClassification:
    source_record_key: str
    acquisition_surface: str
    document_role: str                 # FINAL_TERMS|SECURITIES_NOTE|ISSUE_DOC|
                                       # BASE_PROSPECTUS|SUPPLEMENT|CORRECTION|
                                       # ADMISSION_RECORD|UNKNOWN
    scope_role: str                    # INSTRUMENT_DEFINING|LIFECYCLE|OUT_OF_SCOPE|UNKNOWN
    instrument_class: Optional[str] = None
    document_family_key: Optional[str] = None
    signals: list[str] = field(default_factory=list)
    confidence: str = "LOW"            # HIGH estructural | MEDIUM | LOW


def _family_key(rec: SourceDocument) -> Optional[str]:
    """Solo evidencia estructural; nunca proximidad temporal."""
    if rec.acquisition_surface == "CNMV_ADMISSION":
        return f"ISSUE_ADM_{rec.registro_oficial}" if rec.registro_oficial else None
    if rec.numfol:
        return f"PROG_{rec.numfol}"
    if rec.registro_oficial:
        base = rec.registro_oficial.split(".")[0].split("-")[0]
        return f"PROG_{base}"
    return None


# ---- senales de rol ----

_TITLES = {
    "FINAL_TERMS": re.compile(
        r"condiciones\s+finales|final\s+terms|condiciones\s+definitivas", re.I),
    "SUPPLEMENT": re.compile(
        r"suplemento\s+(?:del?\s+)?(?:folleto|al\s+folleto|de\s+base)?|"
        r"supplement\s+to\s+the\s+(?:base\s+)?prospectus", re.I),
    "SECURITIES_NOTE": re.compile(
        r"nota\s+sobre\s+los\s+valores|securities\s+note", re.I),
    "BASE_PROSPECTUS": re.compile(
        r"folleto\s+de\s+base|base\s+prospectus|documento\s+de\s+registro",
        re.I),
    "CORRECTION": re.compile(
        r"correcci[oó]n\s+de\s+errores|error\s+note|rectificaci[oó]n", re.I),
}

# anclas de datos obligatorias por rol (>=1 requerida para MEDIUM+)
_ANCHORS = {
    "FINAL_TERMS": [
        r"tipo\s+de\s+inter[eé]s\s+nominal|rate\s+of\s+interest",
        r"fecha\s+de\s+vencimiento|maturity\s+date",
        r"importe\s+nominal|aggregate\s+(?:nominal|principal)",
    ],
    "SECURITIES_NOTE": [
        r"admisi[oó]n\s+a\s+negociaci[oó]n|admission\s+to\s+trading",
        r"descripci[oó]n\s+de\s+los\s+valores|description\s+of\s+the\s+securities",
    ],
    "BASE_PROSPECTUS": [
        r"factores\s+de\s+riesgo|risk\s+factors",
        r"condiciones\s+de\s+los\s+valores|terms\s+and\s+conditions",
    ],
}

_DEBT_DENOM = re.compile(
    r"BONOS|OBLIG|C[EÉ]DULAS?|PAGAR[ÉE]S?|RENTA\s+FIJA|FTA\b|TITULIZACI",
    re.I)


def classify(rec: SourceDocument) -> DocumentClassification:
    """Cascada auditable. Devuelve UNKNOWN si no hay evidencia suficiente."""
    sig: list[str] = []
    cl = DocumentClassification(
        source_record_key=rec.source_record_key,
        acquisition_surface=rec.acquisition_surface,
        document_role="UNKNOWN", scope_role="UNKNOWN",
        instrument_class=None,
        document_family_key=_family_key(rec))

    # 1. metadatos estructurados de fuente (la mas fuerte)
    meta_role = (rec.source_meta.get("rol") or "").upper()
    if rec.acquisition_surface == "CNMV_CCFF":
        sig.append("surface:CNMV_CCFF row = condiciones finales")
        cl.document_role, cl.scope_role = "FINAL_TERMS", "INSTRUMENT_DEFINING"
        cl.confidence = "HIGH"
    elif "SUPLEMENTO" in meta_role or re.search(r"\.\d+$", rec.registro_oficial or ""):
        sig.append("meta:rol=SUPLEMENTO / sufijo .k")
        cl.document_role, cl.scope_role = "SUPPLEMENT", "LIFECYCLE"
        cl.confidence = "HIGH"
    elif "MODIFICACI" in meta_role or re.search(r"-\d+$", rec.registro_oficial or ""):
        sig.append("meta:rol=MODIFICACION / sufijo -k")
        cl.document_role, cl.scope_role = "CORRECTION", "LIFECYCLE"
        cl.confidence = "HIGH"
    elif rec.acquisition_surface in ("CNMV_FOLLETOS_EMISION",
                                     "CNMV_FOLLETO_DETAIL"):
        # fila de folleto sin marca de suplemento/modificacion:
        # documento de registro/base prospectus del programa
        sig.append(f"surface:{rec.acquisition_surface} row = folleto base")
        cl.document_role = "BASE_PROSPECTUS"
        cl.scope_role = "INSTRUMENT_DEFINING"
        cl.confidence = "HIGH"
    elif rec.acquisition_surface == "CNMV_ADMISSION":
        sig.append("surface:CNMV_ADMISSION")
        denom = rec.source_meta.get("denominacion") or ""
        if _DEBT_DENOM.search(denom):
            cl.document_role = "SECURITIES_NOTE"
            cl.scope_role = "INSTRUMENT_DEFINING"
            cl.instrument_class = "DEBT"
            sig.append(f"meta:denominacion={denom[:40]}")
        else:
            cl.document_role, cl.scope_role = "ISSUE_DOC", "OUT_OF_SCOPE"
        cl.confidence = "HIGH"

    # 2-4. titulo + anclas + firmas sobre head_text acotado
    head = (rec.head_text or "")[:HEADER_WINDOW]
    for role, rx in _TITLES.items():
        if rx.search(head):
            sig.append(f"title:{role}")
            if cl.document_role == "UNKNOWN":
                cl.document_role = role
                cl.confidence = "MEDIUM"
            elif cl.document_role == "ISSUE_DOC" and role == "SECURITIES_NOTE":
                # admision sin denominacion de deuda pero el propio
                # documento se titula 'securities note': el titulo
                # explicito corrige el fallback por defecto
                cl.document_role, cl.scope_role = \
                    "SECURITIES_NOTE", "INSTRUMENT_DEFINING"
                cl.instrument_class = "DEBT"
                sig.append("title_overrides_default:securities_note")
            elif cl.document_role != role:
                sig.append(f"conflict:meta={cl.document_role}!={role}")
                if cl.confidence == "HIGH":
                    # una mencion en prosa no reclasifica, pero el
                    # desacuerdo titulo/meta rebaja la confianza a
                    # revisable
                    cl.confidence = "MEDIUM"
            break
    if cl.document_role in _ANCHORS:
        hits = [a for a in _ANCHORS[cl.document_role] if re.search(a, head, re.I)]
        if hits:
            sig.append(f"anchors:{len(hits)}")
            if cl.confidence == "MEDIUM":
                cl.confidence = "HIGH"
        elif cl.confidence == "MEDIUM":
            sig.append("anchors:none -> confidence stays MEDIUM")

    # 5. scope/instrument por metadato si aun abierto
    if cl.scope_role == "UNKNOWN":
        if cl.document_role == "SUPPLEMENT":
            cl.scope_role = "LIFECYCLE"
        elif cl.document_role in ("FINAL_TERMS", "SECURITIES_NOTE",
                                  "BASE_PROSPECTUS"):
            cl.scope_role = "INSTRUMENT_DEFINING"
    if cl.instrument_class is None and _DEBT_DENOM.search(
            rec.source_meta.get("denominacion", "") or
            rec.source_meta.get("tipo_valor", "") or ""):
        cl.instrument_class = "DEBT"
        sig.append("instrument:DEBT(meta)")

    if cl.document_role == "UNKNOWN":
        sig.append("fallback:UNKNOWN -> REVIEW_REQUIRED")
        cl.confidence = "LOW"
    cl.signals = sig
    return cl
