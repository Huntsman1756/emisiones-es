"""ExerciseTerms — call/put como estructura, no list[date] (AMEND-2 §10).

Referencia semantica: QuantLib Callability{price, Call|Put, date}+Schedule;
OpenGamma Strata. No se copia logica de pricing.

Compatibilidad: `call_dates`/`put_dates` se derivan como vista de
exercise_dates para scoring con el contrato G0.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from emissions_es.model import EvidencePointer, TermObservation


class OptionSide(str, Enum):
    CALL = "CALL"   # derecho del emisor (reembolso anticipado a su opcion)
    PUT = "PUT"     # derecho del titular/inversor


class ExerciseTerms(BaseModel):
    option_side: OptionSide
    exercise_dates: Optional[TermObservation] = None
    exercise_window: Optional[TermObservation] = None
    exercise_price: Optional[TermObservation] = None
    price_type: Optional[TermObservation] = None   # % nominal / make-whole / ...
    notice_period: Optional[TermObservation] = None
    conditions: Optional[TermObservation] = None
    evidence: list[EvidencePointer] = Field(default_factory=list)
