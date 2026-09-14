"""FinalTermsExtractor — condiciones finales CNMV (ICMA-style).

CUSTOM delta CNMV: vocabulario ES/EN de etiquetas y layouts de tabla
caracteristicos de las condiciones finales espanolas. El pipeline
(locate -> extract -> verify -> invariants) es patron portado.

Familias de campos:
  coupon_family  (tipo, fijo, benchmark, spread, frecuencia, day_count)
  exercise       (call/put como ExerciseTerms con option_side)
  core           (isin, currency, issue/maturity, importes)
  structured     (subyacente, barreras separadas por funcion)
"""
from __future__ import annotations

import re

from emissions_es.extraction.common.base import FamilyExtractor
from emissions_es.extraction.common.region_view import RegionView
from emissions_es.extraction.common.result import (ExtractionResult,
                                                   FailureClass)
from emissions_es.extraction.extractors import FIELD_SPECS, extract_field
from emissions_es.model import FactStatus
from emissions_es.terms.daycount import resolve_daycount

SECTIONS = {
    "interest": re.compile(
        r"tipo\s+de\s+inter[eé]s|rate\s+of\s+interest|interest\s+basis|"
        r"cup[oó]n|eur[ií]bor|day\s+count|base\s+de\s+c[aá]lculo", re.I),
    "redemption": re.compile(
        r"reembolso|amortizaci[oó]n|redemption|vencimiento|maturity", re.I),
    "exercise": re.compile(
        r"opci[oó]n(?:es)?\s+de\s+amortizaci[oó]n|amortizaci[oó]n\s+anticipada|"
        r"call\s+option|put\s+option|issuer\s+call|put/call|"
        r"early\s+redemption|reembolso\s+anticipado|autocall", re.I),
    "general": re.compile(
        r"\bisin\b|divisa|currency|denominaci[oó]n|importe\s+nominal|"
        r"importe\s+total|importe\s+nominal\s+y\s+efectivo|"
        r"aggregate\s+(?:nominal|principal|amount)", re.I),
    "structured": re.compile(
        r"subyacente|underlying|barrera|barrier|strike|participaci[oó]n|"
        r"observation|observaci[oó]n", re.I),
}

FIELD_SECTION = {
    "isin": "general", "currency": "general", "issue_date": "general",
    "maturity": "general", "denomination": "general",
    "issued_amount": "general",
    "coupon_type": "interest", "coupon_rate": "interest",
    "benchmark": "interest", "spread": "interest",
    "payment_frequency": "interest", "day_count": "interest",
    "business_day_convention": "interest",
    "call_dates": "exercise", "put_dates": "exercise",
    "reset_dates": "interest", "fixing_rules": "interest",
    "ranking": "general", "subordination": "general",
}


class FinalTermsExtractor(FamilyExtractor):
    family_id = "final_terms"
    supported_roles = ("FINAL_TERMS",)
    section_patterns = SECTIONS
    field_sections = FIELD_SECTION

    def extract(self, view, regions: dict) -> dict:
        out = {}
        for spec in FIELD_SPECS:
            section = self.field_sections.get(spec.field)
            rgs = regions.get(section) or []
            if section and not rgs:
                out[spec.field] = ExtractionResult(
                    field=spec.field, failure=FailureClass.LOCATION_MISS,
                    failure_detail=f"seccion '{section}' sin region candidata")
                continue
            # recorre las regiones en orden de densidad; primera que
            # produzca observacion gana
            obs = None
            for rg in sorted(rgs, key=lambda r: -r.score) or [None]:
                scoped = RegionView(view, rg) if rg is not None else view
                o = extract_field(scoped, spec, self.family_id, self.version)
                if o.status != FactStatus.MISSING:
                    obs = o
                    break
                obs = obs or o
            out[spec.field] = self._to_result(spec, obs, len(rgs))
        return out

    def post_process(self, view, out: dict) -> dict:
        """Canonical semantics sobre observaciones ya verificadas.

        day_count: lexema -> DayCountCanonical (mapping versionado).
        '1/1' exige contexto de day-count en el item/fila.
        """
        res = out.get("day_count")
        if res and res.observation and res.observation.raw_lexeme:
            lex = res.observation.raw_lexeme
            ctx = " ".join(e.text_excerpt or "" for e in res.observation.evidence)
            m = resolve_daycount(lex, ctx or lex)
            if m is not None:
                res.observation.value = m.canonical
                res.observation.confidence_class = (
                    res.observation.confidence_class or "") + "+canonical"
            elif m is None and res.observation.status == FactStatus.DERIVED:
                res.observation.status = FactStatus.OBSERVED
                res.observation.value = None
                res.observation.confidence_class = "unmapped_lexeme"
        return out

    def _to_result(self, spec, obs, n_regions) -> ExtractionResult:
        if obs.status == FactStatus.MISSING:
            return ExtractionResult(field=spec.field, observation=obs,
                                    failure=FailureClass.PARSING_MISS,
                                    located_regions=n_regions)
        return ExtractionResult(field=spec.field, observation=obs,
                                located_regions=n_regions)
