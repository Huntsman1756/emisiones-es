"""Primitivas de reconciliacion entre fuentes.

Nunca selecciona silenciosamente 'la mejor fuente': conserva todas las
observaciones y clasifica la relacion entre ellas.
"""
from __future__ import annotations

from emissions_es.model import (FactStatus, ReconciliationObservation,
                                ReconciliationStatus, TermObservation)


def reconcile(field: str, subject_key: str,
              observations: list[TermObservation],
              ) -> ReconciliationObservation:
    """Cruza observaciones del mismo campo/sujeto desde fuentes distintas.

    - 0 observaciones          -> MISSING
    - 1 observacion            -> SOURCE_ONLY
    - valores iguales          -> AGREE
    - valores distintos        -> CONFLICT (todas conservadas)
    - alguna MISSING           -> NOT_APPLICABLE si el campo no aplica
    """
    obs = [o for o in observations if o.status != FactStatus.MISSING]
    if not observations:
        return ReconciliationObservation(field=field, subject_key=subject_key,
                                         status=ReconciliationStatus.MISSING)
    if not obs:
        return ReconciliationObservation(field=field, subject_key=subject_key,
                                         status=ReconciliationStatus.MISSING,
                                         observations=observations)
    if len(obs) == 1:
        return ReconciliationObservation(field=field, subject_key=subject_key,
                                         status=ReconciliationStatus.SOURCE_ONLY,
                                         observations=obs)
    vals = {_norm_val(o.value) for o in obs}
    if len(vals) == 1:
        return ReconciliationObservation(field=field, subject_key=subject_key,
                                         status=ReconciliationStatus.AGREE,
                                         observations=obs)
    return ReconciliationObservation(field=field, subject_key=subject_key,
                                     status=ReconciliationStatus.CONFLICT,
                                     observations=obs)


def _norm_val(v) -> str:
    if isinstance(v, dict):
        # money dicts: comparar amount+currency normalizados
        return f"{v.get('amount')}|{v.get('currency')}"
    return str(v).strip() if v is not None else ''
