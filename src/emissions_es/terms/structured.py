"""StructuredProductTerms — `barrier` queda abolido (AMEND-2 §1).

Tres conceptos distintos, no variantes de un campo:
  autocall_trigger    — condicion de reembolso anticipado automatico
  coupon_barrier      — condicion de pago del cupon
  protection_barrier  — condicion de perdida de capital

Referencia semantica/oracle: mattkorman/structured-products-toolkit (MIT,
PORT_PATTERN/REFERENCE en upstream-registry). No se adopta su extractor.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from emissions_es.model import TermObservation


class BarrierKind(str, Enum):
    AUTOCALL_TRIGGER = "autocall_trigger"
    COUPON_BARRIER = "coupon_barrier"
    PROTECTION_BARRIER = "protection_barrier"


class AutocallTerms(BaseModel):
    trigger: Optional[TermObservation] = None
    observation_schedule: Optional[TermObservation] = None
    redemption_terms: Optional[TermObservation] = None


class StructuredCouponTerms(BaseModel):
    rate: Optional[TermObservation] = None
    barrier: Optional[TermObservation] = None
    memory: Optional[TermObservation] = None
    observation_schedule: Optional[TermObservation] = None


class ProtectionTerms(BaseModel):
    barrier: Optional[TermObservation] = None
    barrier_style: Optional[TermObservation] = None   # european/american/etc.
    strike: Optional[TermObservation] = None
    loss_formula: Optional[TermObservation] = None


class StructuredProductTerms(BaseModel):
    underlying: Optional[TermObservation] = None
    initial_level: Optional[TermObservation] = None
    strike: Optional[TermObservation] = None
    autocall: AutocallTerms = Field(default_factory=AutocallTerms)
    coupon: StructuredCouponTerms = Field(default_factory=StructuredCouponTerms)
    protection: ProtectionTerms = Field(default_factory=ProtectionTerms)
    participation: Optional[TermObservation] = None
    cap: Optional[TermObservation] = None
    settlement_type: Optional[TermObservation] = None
