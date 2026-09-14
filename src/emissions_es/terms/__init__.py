"""Canonical term models G1 (AMEND-2, commit 417917d).

Modulo propio de semantica canonica; los mappings a CDM/QuantLib/Strata son
versionados y referenciales — no se vendorea el enum CDM literal.
"""
from emissions_es.terms.daycount import (DAYCOUNT_CANONICAL, DayCountMapping,
                                         resolve_daycount)
from emissions_es.terms.coupon import CouponTerms, CouponType
from emissions_es.terms.exercise import ExerciseTerms, OptionSide
from emissions_es.terms.structured import (BarrierKind, StructuredProductTerms)

__all__ = [
    "DAYCOUNT_CANONICAL", "DayCountMapping", "resolve_daycount",
    "CouponTerms", "CouponType", "ExerciseTerms", "OptionSide",
    "BarrierKind", "StructuredProductTerms",
]
