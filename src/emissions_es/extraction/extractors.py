"""Extractores deterministas primera ola (G0-C).

Reglas:
- Semantica antes que normalizacion: solo se acepta un valor si aparece
  bajo un ancla explicita (label ICMA/ES). Nunca se promueve un numero
  por plausibilidad.
- Toda observacion conserva raw_lexeme + evidence (page/bbox/charspan
  via Docling provenance).
- status: DERIVED para valores normalizados a partir del lexema
  observado; MISSING cuando el ancla no produce valor; CONFLICT si
  hay observaciones incompatibles.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from emissions_es.extraction.docview import NormalizedDocumentView
from emissions_es.extraction.normalize import (ISIN_RX, norm_currency,
                                               norm_date, norm_money,
                                               norm_number, norm_percent)
from emissions_es.model import FactStatus, TermObservation

NA_RX = re.compile(r'^\s*(not\s+applicable|n/?a|no\s+aplica)\s*\.?\s*$', re.I)


@dataclass
class FieldSpec:
    field: str
    anchors: list[str]                      # regex de etiquetas (EN/ES)
    normalizer: str                         # 'percent'|'date'|'money'|'currency'|'number'|'text'|'isin'
    doc_roles: tuple = ('final_terms', 'base_prospectus', 'supplement',
                      'admission_doc', 'registration_doc', 'issue_document')
    instrument_types: tuple = ('*',)
    strategy: str = 'label_value'


@dataclass
class Extractor:
    extractor_id: str
    version: str
    spec: FieldSpec


NORMALIZERS: dict[str, Callable] = {
    'percent': norm_percent, 'date': norm_date, 'money': norm_money,
    'currency': norm_currency, 'number': norm_number,
}


def _is_na(s: str) -> bool:
    return not s.strip() or bool(NA_RX.match(s))


SUB_RX = re.compile(
    r'^\s*(?:\([a-z0-9]+\)|series|tranche|total|importe|nominal)\b', re.I)


def _resolve_value(view, label_item):
    """label_item sin valor -> valor a la derecha; si no, subfila."""
    v2 = view.value_right_of(label_item)
    if v2 is not None:
        return (getattr(v2, 'text', '') or '').strip(), v2
    sub = view.label_below(label_item)
    if sub is not None and SUB_RX.match((getattr(sub, 'text', '') or '').strip()):
        sv = view.value_right_of(sub)
        if sv is not None:
            return (getattr(sv, 'text', '') or '').strip(), sv
        st = (getattr(sub, 'text', '') or '')
        m2 = re.match(r'^[^:]+:\s*(.+)$', st)
        if m2:
            return m2.group(1).strip(), sub
    return '', None


def _label_value_from_texts(view: NormalizedDocumentView, anchor_rx):
    """Items 'Label: value'; soporta etiqueta partida en dos items
    ('Aggregate Nominal' + 'Amount:') y resolucion geometrica."""
    items = list(view.iter_text_blocks())
    for i, t in enumerate(items):
        txt = (getattr(t, 'text', '') or '').strip()
        if not txt:
            continue
        m = anchor_rx.match(txt)
        label_item = t
        merged = False
        if not m and i + 1 < len(items):
            nxt = items[i + 1]
            joined = txt + ' ' + (getattr(nxt, 'text', '') or '').strip()
            m = anchor_rx.match(joined)
            if m:
                label_item, merged = nxt, True
        if not m:
            continue
        val = m.group('value').strip()
        if val:
            yield val, label_item
            continue
        if merged:
            # el valor puede estar a la derecha de CUALQUIERA de las
            # dos lineas del label partido
            v, it = _resolve_value(view, t)
            if it is not None:
                yield v, it
                continue
        v, it = _resolve_value(view, label_item)
        if it is not None:
            yield v, it


def _label_value_from_tables(view: NormalizedDocumentView, anchor_rx):
    """Tablas label->value: el ancla debe abrir la celda (no mid-string);
    el valor es la primera celda no vacia posterior a la del label.
    Si la fila no trae valor, se miran subfilas (Series/Tranche/Total)."""
    sub_rx = SUB_RX
    for tv in view.iter_tables():
        rows = tv.rows_text()
        for ri, row in enumerate(rows):
            for ci, cell in enumerate(row):
                if not cell or not anchor_rx.match(cell):
                    continue
                # valor en la misma fila tras la celda del label
                val = ''
                for c2 in row[ci + 1:]:
                    if c2 and not anchor_rx.match(c2):
                        val = c2
                        break
                if not val:
                    # subfilas (p.ej. 'Series: USD 25,000,000')
                    for nrow in rows[ri + 1:ri + 3]:
                        nc = [c for c in nrow if c]
                        if nc and sub_rx.match(nc[0]):
                            val = nc[-1]
                            break
                yield val, tv.item


# prefijo opcional de numeracion ICMA: '(i)', '(xxii)', '45.', '(b)'...
NUM_PREFIX = r'(?:\(\s*[a-zivx0-9]+\s*\)|\d+\.?|[a-z]\))?\s*'
# un valor que empieza por verbo es fuga de frase, no un dato
VERB_LEAK = re.compile(r'^\s*(is|are|was|were|shall|means|ser|es|son)\b', re.I)
# '[[   ] per cent. Fixed Rate]' en un folleto base es plantilla sin
# cumplimentar, no un hecho del instrumento
_PLACEHOLDER = re.compile(r'\[[\[\]\s●…\.]*\]|\[●\]')


def _placeholder(v: str) -> bool:
    return bool(_PLACEHOLDER.search(v)) and not re.search(r'\d', v)


def extract_field(view: NormalizedDocumentView, spec: FieldSpec,
                  extractor_id: str, version: str) -> TermObservation:
    anchor_rx = re.compile(
        NUM_PREFIX + r'(?P<label>' + '|'.join(spec.anchors) +
        r')\s*[:\-]?\s*(?P<value>.{0,200})',
        re.I)
    found = []
    for val, item in _label_value_from_texts(view, anchor_rx):
        found.append((val, item))
    for val, item in _label_value_from_tables(view, anchor_rx):
        found.append((val, item))
    if spec.normalizer == 'isin' and not found:
        # el lexema ISIN es auto-ancla; admite 'Codigo ISIN: XX...' en un
        # item y el ISIN standalone como item propio
        for t in view.iter_text_blocks():
            txt = (getattr(t, 'text', '') or '').strip()
            if ISIN_RX.fullmatch(txt):
                found.append((txt, t))
            elif re.search(r'ISIN', txt, re.I):
                m = ISIN_RX.search(txt)
                if m:
                    found.append((m.group(0), t))

    found = [(v, it) for v, it in found
             if v and not VERB_LEAK.match(v) and not _placeholder(v)]
    if not found:
        return TermObservation(field=spec.field, status=FactStatus.MISSING,
                               extractor=extractor_id, extractor_version=version)

    obs = []
    for raw, item in found:
        if _is_na(raw):
            obs.append(TermObservation(
                field=spec.field, raw_lexeme=raw.strip(), value='NOT_APPLICABLE',
                status=FactStatus.OBSERVED, confidence_class='explicit_na',
                evidence=[view.evidence_for(item, extractor_id)] if view.evidence_for(item, extractor_id) else [],
                extractor=extractor_id, extractor_version=version))
            continue
        nv = raw.strip()
        if spec.normalizer in NORMALIZERS:
            out = NORMALIZERS[spec.normalizer](raw)
            if out is None:
                continue          # lexema no normalizable: no promover
            nv = out
        elif spec.normalizer == 'isin':
            m = ISIN_RX.search(raw) or ISIN_RX.search(
                getattr(item, 'text', '') or '')
            if not m:
                continue
            nv = m.group(0)
        ev = view.evidence_for(item, extractor_id)
        if ev is not None:
            ev.text_excerpt = raw.strip()[:300]
        obs.append(TermObservation(
            field=spec.field, raw_lexeme=raw.strip(), value=nv,
            status=FactStatus.DERIVED, confidence_class='anchored',
            evidence=[ev] if ev else [],
            extractor=extractor_id, extractor_version=version))

    if not obs:
        return TermObservation(field=spec.field, status=FactStatus.MISSING,
                               extractor=extractor_id, extractor_version=version)
    vals = {str(o.value) for o in obs}
    if len(vals) > 1:
        # conservar todas: conflicto real (p.ej. series/tramos)
        return TermObservation(field=spec.field, status=FactStatus.CONFLICT,
                               extractor=extractor_id,
                               extractor_version=version,
                               evidence=[e for o in obs for e in o.evidence],
                               value=[o.value for o in obs])
    return obs[0]


FIELD_SPECS: list[FieldSpec] = [
    FieldSpec('isin', [r'\bISIN\b', r'C[oó]digo\s+ISIN'], 'isin'),
    FieldSpec('currency', [r'Specified\s+Currenc(?:y|ies)(?:\s+or\s+Currencies)?',
                           r'Divisa\s+de\s+la\s+emisi[oó]n', r'Divisa\b',
                           r'Moneda\s+de\s+denominaci[oó]n'], 'currency'),
    FieldSpec('issue_date', [r'\bIssue\s+Date\b', r'Fecha\s+de\s+emisi'],
              'date'),
    FieldSpec('maturity', [r'\bMaturity\s+Date\b', r'Fecha\s+de\s+vencimiento',
                           r'Vencimiento\b'], 'date'),
    FieldSpec('denomination', [r'Specified\s+Denomination',
                               r'Denominaci[oó]n\s+unitaria',
                               r'Valor\s+nominal\s+unitario',
                               r'Importe\s+unitario\s+de\s+los\s+[Vv]alores',
                               r'Nominal\s+unitario'], 'money'),
    FieldSpec('issued_amount', [r'Aggregate\s+(?:Principal|Nominal)\s+Amount(?:\s+of\s+(?:the\s+)?Notes)?',
                                r'Importe\s+(?:nominal\s+)?total\s+de\s+la\s+emisi[oó]n',
                                r'Importe\s+de\s+la\s+[Ee]misi[oó]n',
                                r'por\s+un\s+importe\s+(?:nominal\s+)?(?:total\s+)?de'],
              'money'),
    FieldSpec('coupon_type', [r'Interest\s+Basis', r'Tipo\s+de\s+inter[eé]s\b'],
              'text'),
    FieldSpec('coupon_rate', [r'Rate\s+of\s+Interest\b',
                              r'Tipo\s+de\s+inter[eé]s\s+nominal',
                              r'Tipo\s+de\s+inter[eé]s\b(?!\s*(?:fijo|variable|inicial|m[ií]nimo|m[aá]ximo|indexado|de\s+demora))'],
              'percent'),
    FieldSpec('benchmark', [r'Floating\s+Rate\s+Option',
                            r'Tipo\s+de\s+referencia',
                            r'Reference\s+Rate\s*:',
                            r'\bEURIBOR\s*\d*\s*(?:mes|month)'], 'text'),
    FieldSpec('spread', [r'\bMargin[s]?\s*:', r'\bSpread\b', r'Margen\s*:'],
              'percent'),
    FieldSpec('payment_frequency', [r'Interest\s+Payment\s+Date\(s\)?',
                                    r'Fechas?\s+de\s+pago\s+de\s+(?:los\s+)?(?:intereses|cupones)'],
              'text'),
    FieldSpec('day_count', [r'Day\s+Count\s+Fraction', r'Base\s+de\s+c[aá]lculo',
                            r'Day\s+Count\s+Basis'], 'text'),
    FieldSpec('call_dates', [r'Optional\s+Redemption\s+Date\(s\)\s*\(Call\)',
                             r'Opci[oó]n\s+de\s+amortizaci[oó]n\s+anticipada'],
              'text'),
    FieldSpec('business_day_convention', [r'Business\s+Day\s+Convention',
                                          r'Convenci[oó]n\s+de\s+d[ií]as\s+h[aá]biles'],
              'text'),
]

EXTRACTORS = [Extractor(f'EXTRACT_{s.field.upper()}', '1.0', s)
              for s in FIELD_SPECS]


def extract_all(view: NormalizedDocumentView, doc_role: str = 'final_terms'
                ) -> list[TermObservation]:
    out = []
    for ex in EXTRACTORS:
        if doc_role not in ex.spec.doc_roles and '*' not in ex.spec.doc_roles:
            continue
        out.append(extract_field(view, ex.spec, ex.extractor_id, ex.version))
    return out
