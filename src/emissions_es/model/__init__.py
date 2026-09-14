"""Modelo canonico minimo para G0-C.

Pydantic v2, sin ORM ni base de datos. Serializacion JSON/JSONL.
Todo valor factual lleva estado + evidencia; nunca se inventa.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------- estados ----------

class FactStatus(str, Enum):
    OBSERVED = "OBSERVED"      # valor explicito en fuente
    DERIVED = "DERIVED"        # transformacion mecanica reproducible
    INFERRED = "INFERRED"      # hipotesis plausible; no es hecho canonico
    CONFLICT = "CONFLICT"      # observaciones incompatibles conservadas
    MISSING = "MISSING"        # ausencia conocida; nunca rellenar


class LinkDecision(str, Enum):
    EXACT_LINK = "EXACT_LINK"
    NO_LINK = "NO_LINK"
    AMBIGUOUS = "AMBIGUOUS"


class DocRole(str, Enum):
    PROGRAMME = "PROGRAMME"
    BASE_PROSPECTUS = "BASE_PROSPECTUS"
    SUPPLEMENT = "SUPPLEMENT"
    FINAL_TERMS = "FINAL_TERMS"
    CORRECTION = "CORRECTION"
    REDEPOSIT = "REDEPOSIT"
    ADMISSION = "ADMISSION"
    REGISTRATION_DOC = "REGISTRATION_DOC"
    ISSUE_DOCUMENT = "ISSUE_DOCUMENT"   # p.ej. Portfolio Documento de Emision
    UNKNOWN = "UNKNOWN"


class RelationType(str, Enum):
    ISSUED_UNDER = "ISSUED_UNDER"
    SUPPLEMENTS = "SUPPLEMENTS"
    CORRECTS = "CORRECTS"
    REPLACES = "REPLACES"
    RELATES_TO = "RELATES_TO"
    DEFINES_TERMS_FOR = "DEFINES_TERMS_FOR"
    ADMISSION_OF = "ADMISSION_OF"


class ReconciliationStatus(str, Enum):
    AGREE = "AGREE"
    CONFLICT = "CONFLICT"
    SOURCE_ONLY = "SOURCE_ONLY"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class IdentifierType(str, Enum):
    CNMV_REGISTRATION_NUMBER = "CNMV_REGISTRATION_NUMBER"  # NO es id de fila
    CNMV_CCFF_ID = "CNMV_CCFF_ID"
    CNMV_NUMFOL = "CNMV_NUMFOL"
    CNMV_FILING_SEQ = "CNMV_FILING_SEQ"
    ISIN = "ISIN"
    LEI = "LEI"
    SOURCE_URL = "SOURCE_URL"
    DOCUMENT_HASH = "DOCUMENT_HASH"
    VENUE_MIC = "VENUE_MIC"
    PORTFOLIO_DOC_ID = "PORTFOLIO_DOC_ID"


# ---------- identificadores cualificados ----------

class QualifiedIdentifier(BaseModel):
    identifier_type: IdentifierType
    identifier_value: str
    source: str
    valid_from: Optional[dt.date] = None
    valid_to: Optional[dt.date] = None


# ---------- evidencia ----------

class EvidencePointer(BaseModel):
    """Puntero reproducible a la evidencia de un hecho."""
    source: str                                  # 'cnmv', 'portfolio_exchange', ...
    source_record_key: str
    document_id: Optional[str] = None
    snapshot_sha256: Optional[str] = None        # raw sha del snapshot usado
    source_url: Optional[str] = None
    retrieved_at: Optional[str] = None

    page: Optional[int] = None                   # Docling ProvenanceItem.page_no
    bbox: Optional[tuple[float, float, float, float]] = None
    charspan: Optional[tuple[int, int]] = None
    text_excerpt: Optional[str] = None           # lexema/contexto observado

    extractor: str = "manual"
    extractor_version: str = "0"


class TermObservation(BaseModel):
    """Un valor factual observado/derivado para un campo contractual."""
    field: str
    raw_lexeme: Optional[str] = None             # lexema literal observado
    value: Optional[Any] = None                  # valor normalizado
    status: FactStatus
    confidence_class: Optional[str] = None       # calidad de evidencia (no sustituye status)
    evidence: list[EvidencePointer] = Field(default_factory=list)
    extractor: str = "manual"
    extractor_version: str = "0"


# ---------- entidades ----------

class SourceObservation(BaseModel):
    """Una captura versionada de una superficie fuente."""
    source: str
    source_family: str
    source_record_key: str
    canonical_url: str
    retrieved_at: str
    observed_at: Optional[str] = None            # fecha que expone la fuente
    http_status: Optional[int] = None
    content_type: Optional[str] = None
    raw_sha256: Optional[str] = None
    normalized_row_sha256: Optional[str] = None
    document_url: Optional[str] = None
    document_sha256: Optional[str] = None
    redirect_chain: list[str] = Field(default_factory=list)


class Issuer(BaseModel):
    issuer_key: str
    name: str
    identifiers: list[QualifiedIdentifier] = Field(default_factory=list)


class Programme(BaseModel):
    programme_key: str
    issuer_key: str
    identifiers: list[QualifiedIdentifier] = Field(default_factory=list)
    name: Optional[str] = None


class Document(BaseModel):
    document_key: str
    role: DocRole
    identifiers: list[QualifiedIdentifier] = Field(default_factory=list)
    issuer_key: Optional[str] = None
    programme_key: Optional[str] = None
    title: Optional[str] = None
    registered_at: Optional[dt.date] = None
    source_observation: Optional[SourceObservation] = None


class DocumentRelation(BaseModel):
    """Edge del document graph. AMBIGUOUS nunca se auto-promueve."""
    from_document_key: str
    to_document_key: str
    relation: RelationType
    decision: LinkDecision
    rule_id: str
    rule_version: str
    evidence: list[EvidencePointer] = Field(default_factory=list)


class Instrument(BaseModel):
    instrument_key: str
    issuer_key: Optional[str] = None
    programme_key: Optional[str] = None
    identifiers: list[QualifiedIdentifier] = Field(default_factory=list)
    instrument_class: Optional[str] = None


class Venue(BaseModel):
    venue_key: str
    name: str
    venue_type: Optional[str] = None             # regulated|mtf|otf|dlt_snl...
    identifiers: list[QualifiedIdentifier] = Field(default_factory=list)


class InstrumentVenue(BaseModel):
    """ADMITTED_TO / TRADED_ON / SETTLED_BY son relaciones distintas."""
    instrument_key: str
    venue_key: str
    relation: str                                # 'ADMITTED_TO'|'TRADED_ON'|'SETTLED_BY'
    status: FactStatus = FactStatus.OBSERVED
    evidence: list[EvidencePointer] = Field(default_factory=list)


class Conflict(BaseModel):
    field: str
    subject_key: str
    observations: list[TermObservation]
    note: Optional[str] = None


class ReconciliationObservation(BaseModel):
    """Resultado de cruzar el mismo hecho entre fuentes."""
    field: str
    subject_key: str                             # p.ej. ISIN
    status: ReconciliationStatus
    observations: list[TermObservation] = Field(default_factory=list)
    note: Optional[str] = None


# nomenclatura del contrato: identificadores cualificados por entidad
DocumentIdentifier = QualifiedIdentifier
InstrumentIdentifier = QualifiedIdentifier
