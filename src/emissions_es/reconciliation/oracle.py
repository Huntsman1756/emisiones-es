"""Oracle determinista minimo de calendario de pagos.

Entrada: TermObservations de payment_frequency, issue_date, maturity,
call_dates. Salida: VALID / INVALID / UNVERIFIABLE.

No sustituye evidencia documental: solo comprueba consistencia interna
del calendario esperable. Determinista, sin QuantLib/Strata (prohibidos
como dependencia de produccion en G0-C).
"""
from __future__ import annotations

import re
from datetime import date

UNVERIFIABLE, VALID, INVALID = 'UNVERIFIABLE', 'VALID', 'INVALID'

_MONTHS = {m.lower(): i for i, m in enumerate(
    'january february march april may june july august september '
    'october november december'.split(), 1)}
_MONTHS.update({m: i for m, i in zip(
    'enero febrero marzo abril mayo junio julio agosto septiembre '
    'octubre noviembre diciembre'.split(), range(1, 13))})

_FREQ = {  # (meses por periodo, nombre canonico)
    'each year': (12, 'annual'), 'cada a': (12, 'annual'),
    'annually': (12, 'annual'),
    'each six months': (6, 'semiannual'), 'semiannually': (6, 'semiannual'),
    'cada seis meses': (6, 'semiannual'),
    'each quarter': (3, 'quarterly'), 'quarterly': (3, 'quarterly'),
    'trimestral': (3, 'quarterly'),
    'each month': (1, 'monthly'), 'monthly': (1, 'monthly'),
    'mensual': (1, 'monthly'),
}


def _to_date(v) -> date | None:
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v)
        except ValueError:
            return None
    return None


def _freq_months(raw: str | None):
    if not raw:
        return None
    r = raw.lower()
    for k in sorted(_FREQ, key=len, reverse=True):
        if k in r:
            return _FREQ[k]
    # '5 August in each year' / '10 de septiembre de cada ano'
    if re.search(r'each\s+year|cada\s+a[ñn]o|anual', r):
        return (12, 'annual')
    return None


def expected_schedule(frequency_raw: str | None,
                      issue: date | None, maturity: date | None):
    """Devuelve (status, detalle).

    UNVERIFIABLE si falta alguna entrada o la frecuencia no se reconoce.
    """
    if issue is None or maturity is None:
        return UNVERIFIABLE, 'faltan issue_date/maturity'
    if maturity <= issue:
        return INVALID, f'maturity {maturity} <= issue {issue}'
    fm = _freq_months(frequency_raw)
    if fm is None:
        return UNVERIFIABLE, f'frecuencia no reconocible: {frequency_raw!r}'
    step, name = fm
    # generar fechas esperables: mismo dia/mes ciclico desde issue->maturity
    expected = []
    y, m, d = issue.year + step // 12, issue.month + step % 12, issue.day
    if m > 12:
        y += 1; m -= 12
    while True:
        try:
            nxt = date(y, m, d)
        except ValueError:  # dia inexistente en el mes (p.ej. 31/04)
            # ultimo dia del mes
            if m == 12:
                nxt = date(y, 12, 31)
            else:
                nxt = date(y, m + 1, 1) if m < 12 else None
                nxt = nxt - date.resolution if nxt else None
        if nxt is None or nxt > maturity:
            break
        expected.append(nxt)
        m += step
        while m > 12:
            y += 1; m -= 12
    if not expected:
        return INVALID, (f'ninguna fecha de pago encaja entre {issue} y '
                         f'{maturity} con frecuencia {name}')
    if expected[-1] != maturity and (maturity - expected[-1]).days > step * 40:
        return INVALID, (f'ultima fecha esperable {expected[-1]} muy lejos '
                         f'de maturity {maturity}')
    return VALID, {'frequency': name, 'period_months': step,
                   'n_dates': len(expected), 'last': str(expected[-1]),
                   'maturity': str(maturity)}


def check_schedule(observations: dict):
    """observations: {field: TermObservation} -> (status, detalle)."""
    get = lambda k: observations.get(k)
    issue = _to_date(get('issue_date').value) if get('issue_date') else None
    mat = _to_date(get('maturity').value) if get('maturity') else None
    freq_raw = None
    fo = get('payment_frequency')
    if fo is not None:
        freq_raw = fo.raw_lexeme or (str(fo.value) if fo.value else None)
    return expected_schedule(freq_raw, issue, mat)
