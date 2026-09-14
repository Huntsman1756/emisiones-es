"""Failure taxonomy G1 — no todo es MISSING.

Distingue donde murio la cadena:
  LOCATION_MISS       ninguna region candidata contenia la seccion
  PARSING_MISS        region localizada, ningun valor extraido
  NORMALIZATION_MISS  lexema extraido, no normalizable
  VERIFICATION_FAIL   valor extraido pero evidencia no verbatim
  AMBIGUOUS_SOURCE    varios valores incompatibles -> CONFLICT
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from emissions_es.model import TermObservation


class FailureClass(str, Enum):
    LOCATION_MISS = "LOCATION_MISS"
    PARSING_MISS = "PARSING_MISS"
    NORMALIZATION_MISS = "NORMALIZATION_MISS"
    VERIFICATION_FAIL = "VERIFICATION_FAIL"
    AMBIGUOUS_SOURCE = "AMBIGUOUS_SOURCE"


class ExtractionResult(BaseModel):
    """Resultado por campo: observacion + diagnostico de fallo."""
    field: str
    observation: Optional[TermObservation] = None
    failure: Optional[FailureClass] = None
    failure_detail: Optional[str] = None
    located_regions: int = 0
