"""Day-count canonical codes + versioned external mappings.

G1 AMEND-2: codigos canonicos propios; mappings explicitos hacia FINOS CDM,
QuantLib y OpenGamma Strata. No se vendorea DayCountFractionEnum.

Reference pins (docs/g1/upstream-audit.md):
  CDM      finos/common-domain-model  (CSL; mapping only, no literal copy)
  QuantLib lballabio/QuantLib         (BSD-3; reference/oracle)
  Strata   OpenGamma/Strata           (Apache-2.0; reference/oracle)

'1/1' es una convencion ISDA real (FixedRateLegHelper / Bond/'1/1' en QL,
ONE_ONE en CDM). Su aceptacion exige contexto: debe aparecer bajo un ancla
de day-count/day-count-fraction, no como ruido de tabla o enumeracion.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class DayCountMapping:
    """Una convencion canonica + equivalencias versionadas por referencia."""
    canonical: str
    cdm: Optional[str] = None
    quantlib: Optional[str] = None
    strata: Optional[str] = None
    lexemes: tuple = ()          # aliases documentales demostrados (EN/ES)
    needs_context: bool = False  # True si el lexema es ambiguo ('1/1')


DAYCOUNT_CANONICAL: dict[str, DayCountMapping] = {
    "ACT_ACT_ICMA": DayCountMapping(
        "ACT_ACT_ICMA", cdm="ACT_ACT_ICMA", quantlib="ActualActual.ISMA",
        strata="ACT_ACT_ICMA",
        lexemes=("ACT/ACT ICMA", "ACT/ACT (ICMA)", "ACTUAL/ACTUAL (ICMA)",
                 "ACT/ACT-ICMA", "ICMA")),
    "ACT_ACT_ISDA": DayCountMapping(
        "ACT_ACT_ISDA", cdm="ACT_ACT_ISDA", quantlib="ActualActual.ISDA",
        strata="ACT_ACT_ISDA",
        lexemes=("ACT/ACT ISDA", "ACT/ACT (ISDA)", "ACTUAL/ACTUAL (ISDA)",
                 "ACT/ACT-ISDA", "ACT/ACT", "ACTUAL/ACTUAL")),
    "ACT_360": DayCountMapping(
        "ACT_360", cdm="ACT_360", quantlib="Actual360",
        strata="ACT_360",
        lexemes=("ACT/360", "ACTUAL/360", "ACT/360 (ACT/360)")),
    "ACT_365F": DayCountMapping(
        "ACT_365F", cdm="ACT_365L", quantlib="Actual365Fixed",
        strata="ACT_365F",
        lexemes=("ACT/365F", "ACTUAL/365F", "ACTUAL/365 (FIXED)",
                 "ACT/365 FIXED")),
    "ACT_365": DayCountMapping(
        "ACT_365", cdm="ACT_365", quantlib="Actual365",
        strata="ACT_365",
        lexemes=("ACT/365", "ACTUAL/365")),
    "A_30_360": DayCountMapping(
        "A_30_360", cdm="_30_360", quantlib="Thirty360.USA",
        strata="_30_360",
        lexemes=("30/360", "30/360 (30/360)", "BOND BASIS")),
    "A_30E_360": DayCountMapping(
        "A_30E_360", cdm="_30E_360", quantlib="Thirty360.European",
        strata="_30E_360",
        lexemes=("30E/360", "30E/360 (EUROBOND BASIS)", "EUROBOND BASIS")),
    "A_30E_360_ISDA": DayCountMapping(
        "A_30E_360_ISDA", cdm="_30E_360_ISDA",
        quantlib="Thirty360.EurobondBasis", strata="_30E_360_ISDA",
        lexemes=("30E/360 ISDA", "30E/360 (ISDA)")),
    "ONE_ONE": DayCountMapping(
        "ONE_ONE", cdm="_1_1", quantlib="OneDayCounter",
        strata=None,
        lexemes=("1/1",),
        needs_context=True),
}

MAPPING_VERSION = "daycount-map-1.0 (CDM 6.x / QuantLib 1.x / Strata 2.x)"


# anclas de contexto que legitimizan lexemas ambiguos como '1/1'
CONTEXT_ANCHOR = re.compile(
    r"day\s*count|base\s+de\s+c[aá]lculo|fraction|daycount|"
    r"base\s+de\s+c[óo]mputo|m[ée]todo\s+de\s+c[aá]lculo\s+de\s+d[ií]as",
    re.I)

# candidatos lexicos, ordenados de mayor a menor especificidad para
# evitar que 'ACT/ACT' capture 'ACT/ACT ICMA'
_ORDERED = sorted(
    ((m, lx) for m in DAYCOUNT_CANONICAL.values() for lx in m.lexemes),
    key=lambda t: -len(t[1]))

_LEXEME_RX = [
    (m, re.compile(r"(?<![\w/])" + re.escape(lx) + r"(?![\w/])", re.I))
    for m, lx in _ORDERED]


def resolve_daycount(text: str, context: str = "") -> Optional[DayCountMapping]:
    """Lexema documental -> convencion canonica.

    `context` = texto circundante (mismo item/fila). Solo se usa para
    lexemas needs_context ('1/1'): sin ancla de day-count en el contexto
    no se resuelve — el FP de G0 X19 fue de contexto, no de lexema.
    """
    for mapping, rx in _LEXEME_RX:
        if not rx.search(text):
            continue
        if mapping.needs_context and not (
                CONTEXT_ANCHOR.search(context) or CONTEXT_ANCHOR.search(text)):
            return None
        return mapping
    return None
