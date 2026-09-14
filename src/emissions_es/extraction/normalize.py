"""Normalizadores deterministas. Siempre conservan raw_lexeme; el valor
normalizado es DERIVED sobre el lexema OBSERVED."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

MONTHS = {}
for _i, _m in enumerate(['january', 'february', 'march', 'april', 'may', 'june',
                         'july', 'august', 'september', 'october', 'november',
                         'december',
                         'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                         'julio', 'agosto', 'septiembre', 'octubre',
                         'noviembre', 'diciembre']):
    MONTHS[_m] = _i % 12 + 1

CURRENCY_NAMES = {
    'euro': 'EUR', 'euros': 'EUR', 'eur': 'EUR',
    'u.s dollars': 'USD', 'u.s. dollars': 'USD', 'us dollars': 'USD',
    'dollars': 'USD', 'dólares': 'USD', 'dolares': 'USD', 'usd': 'USD',
    'sterling': 'GBP', 'pounds sterling': 'GBP', 'gbp': 'GBP',
    'swiss francs': 'CHF', 'chf': 'CHF', 'yen': 'JPY', 'jpy': 'JPY',
    'renminbi': 'CNH', 'cnh': 'CNH', 'offshore cny': 'CNH', 'cny': 'CNY',
}


def norm_number(s: str) -> Optional[Decimal]:
    """'5,90' / '5.90' / '1.234.567,89' / '25,000,000' -> Decimal.
    Regla: el ultimo separador de , o . es el decimal."""
    s = s.strip().replace('\xa0', ' ').replace(' ', '')
    s = re.sub(r'[^0-9.,\-]', '', s)
    if not s or not re.search(r'\d', s):
        return None
    try:
        if ',' in s and '.' in s:
            # formato mixto: el separador que aparece mas a la derecha es decimal
            if s.rfind(',') > s.rfind('.'):
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')
        elif ',' in s:
            # decimal ES si hay un solo , con <=4 decimales; si no, miles
            if s.count(',') == 1 and len(s.split(',')[1]) <= 4:
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '')
        elif '.' in s and s.count('.') > 1:
            s = s.replace('.', '')
        return Decimal(s)
    except InvalidOperation:
        return None


def norm_percent(s: str) -> Optional[Decimal]:
    m = re.search(r'(-?[0-9][0-9.,]*)\s*(?:%|por ciento|per\s*cent)', s, re.I)
    return norm_number(m.group(1)) if m else None


def norm_date(s: str) -> Optional[str]:
    """'5 August 2036' | '05/08/2036' | '5 de agosto de 2036' -> ISO."""
    s = s.strip()
    m = re.match(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})', s)
    if m:
        d, mo, y = map(int, m.groups())
        if mo <= 12:
            return f'{y:04d}-{mo:02d}-{d:02d}'
        return None
    m = re.search(r'(\d{1,2})\s+(?:de\s+)?([A-Za-záéíóú]+)\s+(?:de\s+)?(\d{4})',
                  s, re.I)
    if m:
        d, mon, y = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        mon = re.sub(r'[^a-z]', '', mon)
        if mon in MONTHS:
            return f'{y:04d}-{MONTHS[mon]:02d}-{d:02d}'
    return None


def norm_currency(s: str) -> Optional[str]:
    s2 = re.sub(r"['\u2019\"()]", '', s).lower()
    s2 = re.sub(r'\s+', ' ', s2).strip()
    for name, iso in sorted(CURRENCY_NAMES.items(), key=lambda kv: -len(kv[0])):
        if name in s2:
            return iso
    m = re.search(r'\b([A-Z]{3})\b', s)
    if m:
        return m.group(1)
    return None


def norm_money(s: str) -> Optional[dict]:
    """'USD 25,000,000' | '500.000.000 euros' -> {amount, currency}."""
    cur = norm_currency(s)
    nums = re.findall(r'[0-9][0-9.,]*', s)
    if not nums:
        return None
    # preferir el numero mas largo (el importe completo)
    raw = max(nums, key=len)
    amt = norm_number(raw)
    if amt is None:
        return None
    return {'amount': str(amt), 'currency': cur, 'raw_number': raw}


ISIN_RX = re.compile(r'\b[A-Z]{2}[0-9A-Z]{9}[0-9]\b')


# ---------- segunda ola: benchmark y frecuencia ----------

# objeto de benchmark identificable: indice + tenor opcional + margen
# opcional. NO acepta prosa alrededor como "valor".
BENCH_NAMES = (r'EURIBOR|EURISOR|€STR|ESTR|EONIA|SONIA|SOFR|LIBOR|MIBOR|'
               r'CMS|CMT|IRPH|BTF|TIPO\s+DE\s+INTER[EÉ]S\s+DE\s+REFERENCIA')
BENCH_RX = re.compile(
    r'\b(' + BENCH_NAMES + r')'
    r'(?:\s*[,\-]?\s*\d+\s*(?:mes(?:es)?|months?|M|a[ñn]os?|years?))?'
    r'(?:\s*(?:a\s+)?(?:6|12)\s*meses)?'
    r'(?:\s*[+\-]\s*[0-9][0-9.,]*\s*%?)?', re.I)


def norm_benchmark(s: str) -> Optional[str]:
    """Extrae el objeto benchmark de un lexema. Rechaza prosa sin
    objeto identificable (p.ej. 's was 2.335% on 3 July 2026…')."""
    m = BENCH_RX.search(s)
    if not m:
        return None
    return re.sub(r'\s+', ' ', m.group(0)).strip(' ,.-')


# centinela: el lexema es real pero no hay un unico valor canonico
# (rango, alternativas, regimen condicional). Conservar raw, no forzar.
RAW_ONLY = object()

_FREQ_TOKENS = [
    ('annual', ('each year', 'cada a\u00f1o', 'cada ano', 'anualmente',
                'annually', 'por a\u00f1o', 'once a year')),
    ('semi_annual', ('each six months', 'cada seis meses', 'semestral',
                     'semi-annual', 'semiannually', 'twice a year')),
    ('quarterly', ('each quarter', 'quarterly', 'trimestral',
                   'cada trimestre', 'each three months',
                   'cada tres meses')),
    ('monthly', ('each month', 'monthly', 'mensual', 'cada mes')),
    ('weekly', ('each week', 'weekly', 'semanal')),
]
# indicadores de que el lexema describe rango/alternativas/regimen,
# no una unica frecuencia
_COMPLEX_FREQ = re.compile(
    r'\b(?:to|hasta)\s+(?:and\s+)?including\b|\bfrom\b.*\bto\b|'
    r'\bcommenc|or\s+the\b|\bpr[oó]rroga|\bextensi|variable|'
    r'alternativ', re.I)


def norm_frequency(s: str):
    """Lexema -> frecuencia canonica | RAW_ONLY | None.

    - exactamente un token de frecuencia -> canonico ('each year' -> ANNUAL)
    - varios tokens distintos (regimen/alternativas) -> RAW_ONLY
    - rango/condicional sin token unico -> RAW_ONLY
    - nada reconocible -> None (no promover)
    """
    r = re.sub(r'\s+', ' ', s.lower())
    # ignorar tokens dentro de corchetes de plantilla: '[in each year]'
    # en un folleto base es una opcion condicional, no un hecho
    r_free = re.sub(r'\[[^\]]*\]', ' ', r)
    hits = {canon for canon, keys in _FREQ_TOKENS
            if any(k in r_free for k in keys)}
    hits_all = {canon for canon, keys in _FREQ_TOKENS
                if any(k in r for k in keys)}
    if len(hits) == 1:
        return hits.pop().upper()
    if hits_all or len(hits) > 1:
        return RAW_ONLY
    if _COMPLEX_FREQ.search(r):
        return RAW_ONLY
    if re.search(r'\b\d{4}\b', r) and ',' in s:
        return RAW_ONLY
    return None
