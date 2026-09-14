"""CouponTerms — modelo canonico de cupon (G1 AMEND-2 §9).

No reduce cupones a `coupon_rate`. Las categorias solo se materializan si
la fuente las publica; nunca se infiere un tipo para completar el enum.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from emissions_es.model import TermObservation


class CouponType(str, Enum):
    FIXED = "FIXED"
    FLOATING = "FLOATING"
    FIXED_TO_FLOATING = "FIXED_TO_FLOATING"
    STEP_UP = "STEP_UP"
    ZERO = "ZERO"
    STRUCTURED = "STRUCTURED"
    OTHER = "OTHER"


class CouponTerms(BaseModel):
    coupon_type: Optional[CouponType] = None
    fixed_rate: Optional[TermObservation] = None
    benchmark: Optional[TermObservation] = None
    spread: Optional[TermObservation] = None
    reset_schedule: Optional[TermObservation] = None
    fixing_rules: Optional[TermObservation] = None
    floor: Optional[TermObservation] = None
    cap: Optional[TermObservation] = None
    payment_frequency: Optional[TermObservation] = None
    day_count: Optional[TermObservation] = None
