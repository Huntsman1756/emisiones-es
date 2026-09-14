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
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Optional

from emissions_es.extraction.docview import NormalizedDocumentView
from emissions_es.extraction.normalize import (ISIN_RX, RAW_ONLY,
                                               norm_applicability,
                                               norm_benchmark, norm_currency,
                                               norm_date, norm_dates_or_text,
                                               norm_frequency, norm_money,
                                               norm_number, norm_percent,
                                               norm_ranking, norm_spread,
                                               norm_subordination,
                                               norm_text_or_percent)
from emissions_es.model import FactStatus, TermObservation

NA_RX = re.compile(
    r'^\s*(not\s+applicable|n/?a|no\s+aplica(?:ble)?|not\s+specified|'
    r'no\s+consta|sin\s+aplicar|no)\s*\.?\s*$',
    re.I)


@dataclass
class FieldSpec:
    field: str
    anchors: list[str]                      # regex de etiquetas (EN/ES)
    normalizer: str                         # 'percent'|'date'|'money'|'currency'|'number'|'text'|'isin'|'spread'|'applicability'|'text_or_percent'|'ranking'|'subordination'|'dates_or_text'
    doc_roles: tuple = ('final_terms', 'base_prospectus', 'supplement',
                      'admission_doc', 'registration_doc', 'issue_document')
    instrument_types: tuple = ('*',)
    strategy: str = 'label_value'
    ver: str = '1.0'
    value_rx: str | None = None   # objeto autocontenido (como ISIN):
                                  # el propio lexema es el valor
    multi: bool = False           # campo multi-aspecto/valor: varias
                                  # observaciones complementarias se emiten
                                  # como lista OBSERVED, no como CONFLICT
                                  # (CONFLICT queda para valores que se
                                  # contradicen sobre el mismo hecho)


@dataclass
class Extractor:
    extractor_id: str
    version: str
    spec: FieldSpec


NORMALIZERS: dict[str, Callable] = {
    'percent': norm_percent, 'date': norm_date, 'money': norm_money,
    'currency': norm_currency, 'number': norm_number,
    'benchmark': norm_benchmark, 'frequency': norm_frequency,
    # segunda ola
    'spread': norm_spread, 'applicability': norm_applicability,
    'text_or_percent': norm_text_or_percent, 'ranking': norm_ranking,
    'subordination': norm_subordination, 'dates_or_text': norm_dates_or_text,
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


_BULLET = re.compile(r'^[•●·▪◦‣\-\*o\s]+')


_SEG = re.compile(r'[·•▪◦‣]')   # separador intra-item de campos


def _label_value_from_texts(view: NormalizedDocumentView, anchor_rx):
    """Items 'Label: value'; soporta etiqueta partida en dos items
    ('Aggregate Nominal' + 'Amount:'), bullets iniciales, resolucion
    geometrica y varios campos en un mismo item separados por '·'."""
    items = list(view.iter_text_blocks())
    for i, t in enumerate(items):
        raw_txt = (getattr(t, 'text', '') or '').strip()
        if not raw_txt:
            continue
        for seg in _SEG.split(raw_txt):
            txt = _BULLET.sub('', seg.strip())
            if not txt:
                continue
            m = anchor_rx.match(txt)
            label_item = t
            merged = False
            if not m and i + 1 < len(items):
                nxt = items[i + 1]
                joined = txt + ' ' + _BULLET.sub(
                    '', (getattr(nxt, 'text', '') or '').strip())
                m = anchor_rx.match(joined)
                if m:
                    label_item, merged = nxt, True
            if not m:
                continue
            val = m.group('value').strip()
            if not m.group('sep') and ':' in val:
                # la etiqueta continua antes de los dos puntos:
                # 'Base de calculo para el devengo de intereses: Act/360'
                # o 'Fecha de Emision/Desembolso: 13 de mayo de 2026'
                val = val.split(':', 1)[1].strip()
            elif not m.group('sep') and \
                    val.lstrip('\'"‘“`').strip()[:1].islower():
                # sin separador y continuacion en minuscula = frase en
                # prosa (checklist 'b) Descripcion del subyacente en
                # que...' / definicion '"Initial Closing Price" means'),
                # no un par etiqueta:valor
                continue
            if merged and val.endswith(':'):
                val = ''      # cola de etiqueta partida, no es el valor
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
                continue
            # label solo: en layouts de dos columnas los valores pueden
            # intercalarse ('label:' / 'No aplicable.' / 'valor'). Escanear
            # los items siguientes y emitir TODOS los candidatos no-etiqueta
            # hasta el primer item etiqueta-like -> CONFLICT honesto si hay
            # ambiguedad de atribucion, nunca promocion por proximidad.
            li = items.index(label_item)
            for nxt in items[li + 1:li + 4]:
                ntxt = _BULLET.sub(
                    '', (getattr(nxt, 'text', '') or '').strip())
                if not ntxt:
                    continue
                if ntxt.endswith(':') or anchor_rx.match(ntxt) \
                        or _LABEL_LIKE.match(ntxt):
                    break
                yield ntxt, nxt


def _label_value_from_tables(view: NormalizedDocumentView, anchor_rx):
    """Tablas label->value: el ancla debe abrir la celda (no mid-string);
    el valor es la primera celda no vacia posterior a la del label.
    Si la fila no trae valor, se miran subfilas (Series/Tranche/Total)."""
    sub_rx = SUB_RX
    for tv in view.iter_tables():
        rows = tv.rows_text()
        # columna de datos vs etiqueta: si el mismo texto de label se
        # repite en >=3 filas de la tabla, es la cabecera de una columna
        # de datos (p.ej. 'Tipo de interes medio' de una cartera
        # titulizada), no una pareja label->valor del instrumento
        label_hits = Counter()
        for row in rows:
            for cell in row:
                cell = _BULLET.sub('', cell or '')
                if cell and anchor_rx.match(cell):
                    label_hits[cell.strip().lower()] += 1
        data_cols = {k for k, n in label_hits.items() if n >= 3}
        for ri, row in enumerate(rows):
            for ci, cell in enumerate(row):
                cell = _BULLET.sub('', cell or '')
                if not cell:
                    continue
                m = anchor_rx.match(cell)
                if not m or cell.strip().lower() in data_cols:
                    continue
                inline = m.group('value').strip()
                if not m.group('sep') and ':' in inline:
                    # 'Label larga: valor' dentro de la misma celda
                    inline = inline.split(':', 1)[1].strip()
                    if inline:
                        yield inline, tv.item
                        continue
                elif not m.group('sep') and inline.lstrip(
                        '\'"‘“`').strip()[:1].islower():
                    # celda-frase: etiqueta sin ':' seguida de prosa en
                    # minuscula (checklist), no encabezado de valor
                    continue
                elif m.group('sep') and inline:
                    # 'Label: valor' inline en una sola celda
                    yield inline, tv.item
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
VERB_LEAK = re.compile(
    r'^\s*["\'‘“`]?\s*(is|are|was|were|shall|means|ser|es|son|'
    r'in\s+relation\s+to|as\s+provided|specified\s+in|de\s+conformidad|'
    r'seg[uú]n)\b', re.I)
# '[[   ] per cent. Fixed Rate]' en un folleto base es plantilla sin
# cumplimentar, no un hecho del instrumento
_PLACEHOLDER = re.compile(r'\[[\[\]\s●…\.]*\]|\[●\]')
# 'See table above' / 'As per Conditions' / 'véase epígrafe': referencia
# a otra parte del documento: evidencia real pero sin valor propio
_XREF = re.compile(
    r'^\s*(?:see|as\s+per|as\s+set\s+out|v[eé]ase|seg[uú]n|conforme\s+a)\b',
    re.I)
# fragmento de etiqueta en posicion de valor: 'Instrument' en
# 'Maturity Redemption Amount of each | Instrument | EUR 100,000'
_LABEL_FRAG = re.compile(
    r'^\s*(?:the\s+)?(?:notes?|instruments?|valores?|obligaciones|'
    r'calculation\s+amount|notes?\s+payable)\s*\.?\s*$', re.I)
# 'Etiqueta: resto' — texto con dos puntos en los primeros 60 chars es
# otra etiqueta, no un valor candidato
_LABEL_LIKE = re.compile(r'^[A-Za-zÁÉÍÓÚÜÑ(][^:]{0,60}\s*:')


def _placeholder(v: str) -> bool:
    return bool(_PLACEHOLDER.search(v)) and not re.search(r'\d', v)


def extract_field(view: NormalizedDocumentView, spec: FieldSpec,
                  extractor_id: str, version: str) -> TermObservation:
    anchor_rx = re.compile(
        NUM_PREFIX + r'(?P<label>' + '|'.join(spec.anchors) +
        r')\s*(?P<sep>[:\-]?)\s*(?P<value>.{0,200})',
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
    if spec.value_rx:
        # el valor es un objeto autocontenido que puede vivir dentro de
        # un item o celda (p.ej. 'Modified Following Business Day
        # Convention' embebida en el valor de Interest Payment Dates)
        vrx = re.compile(spec.value_rx, re.I)
        for t in view.iter_text_blocks():
            txt = (getattr(t, 'text', '') or '').strip()
            for m in vrx.finditer(txt):
                found.append((m.group(0), t))
        for tv in view.iter_tables():
            for row in tv.rows_text():
                for c in row:
                    c = _BULLET.sub('', c or '')
                    for m in vrx.finditer(c):
                        found.append((m.group(0), tv.item))

    found = [(v, it) for v, it in found
             if v and not VERB_LEAK.match(v) and not _placeholder(v)
             and not _LABEL_FRAG.match(v)]
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
        if _XREF.match(raw.strip()):
            ev = view.evidence_for(item, extractor_id)
            if ev is not None:
                ev.text_excerpt = raw.strip()[:300]
            obs.append(TermObservation(
                field=spec.field, raw_lexeme=raw.strip(), value=None,
                status=FactStatus.OBSERVED,
                confidence_class='cross_reference',
                evidence=[ev] if ev else [],
                extractor=extractor_id, extractor_version=version))
            continue
        nv = raw.strip()
        raw_only = False
        if spec.normalizer in NORMALIZERS:
            out = NORMALIZERS[spec.normalizer](raw)
            if out is None and spec.normalizer == 'benchmark':
                # el objeto benchmark puede vivir en el item completo:
                # '(iii) EURIBOR 3 months was 2.335%…'
                out = norm_benchmark(getattr(item, 'text', '') or '')
            if out is None:
                continue          # lexema no normalizable: no promover
            if out is RAW_ONLY:
                # prosa real (rango/alternativas/regimen): conservar
                # lexema como OBSERVED, sin valor canonico
                raw_only = True
            else:
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
            field=spec.field, raw_lexeme=raw.strip(),
            value=None if raw_only else nv,
            status=(FactStatus.OBSERVED if raw_only
                    else FactStatus.DERIVED),
            confidence_class='raw_only' if raw_only else 'anchored',
            evidence=[ev] if ev else [],
            extractor=extractor_id, extractor_version=version))

    if not obs:
        return TermObservation(field=spec.field, status=FactStatus.MISSING,
                               extractor=extractor_id, extractor_version=version)
    # 'Determinacion ISDA: No Aplicable' + 'Pantalla Relevante: Reuters':
    # el NA pertenece a un mecanismo alternativo, no contradice el valor
    # real; no genera CONFLICT
    non_na = [o for o in obs if o.value != 'NOT_APPLICABLE']
    if non_na:
        obs = non_na
    # mezcla valor normalizado + lexema crudo ('Optional Redemption
    # Dates (Call): 9 April 2029' + 'Call Option: Applicable'): el valor
    # concreto gana, los raw quedan como evidencia adicional
    valued = [o for o in obs if o.value is not None]
    if len({str(o.value) for o in valued}) == 1:
        keep = valued[0]
        keep.evidence = [e for o in obs for e in o.evidence]
        return keep
    vals = {str(o.value) for o in obs}
    if len(vals) > 1:
        # dedupe por contencion: 'Delivery against payment' y
        # 'against payment' son el mismo hecho con distinta
        # granularidad; conservar el mas completo
        strvals = [str(o.value) for o in obs if o.value is not None]
        drop = {a for a in strvals
                if any(a != b and a in b for b in strvals)}
        keep = [o for o in obs
                if o.value is None or str(o.value) not in drop]
        vals = {str(o.value) for o in keep}
        if len(vals) == 1:
            return keep[0]
        if spec.multi:
            # aspectos complementarios del mismo campo (p.ej. pantalla +
            # fecha de determinacion + procedimiento de publicacion):
            # lista OBSERVED, cada elemento conserva su evidencia
            return TermObservation(
                field=spec.field, status=FactStatus.OBSERVED,
                confidence_class='multi_aspect',
                value=[o.value if o.value is not None else o.raw_lexeme
                       for o in keep],
                evidence=[e for o in keep for e in o.evidence],
                extractor=extractor_id, extractor_version=version)
        # conservar todas: conflicto real (p.ej. series/tramos)
        return TermObservation(field=spec.field, status=FactStatus.CONFLICT,
                               extractor=extractor_id,
                               extractor_version=version,
                               evidence=[e for o in keep for e in o.evidence],
                               value=[o.value for o in keep])
    return obs[0]


FIELD_SPECS: list[FieldSpec] = [
    FieldSpec('isin', [r'\bISIN\b', r'C[oó]digo\s+ISIN'], 'isin'),
    FieldSpec('currency', [r'Specified\s+Currenc(?:y|ies)(?:\s+or\s+Currencies)?',
                           r'Divisa\s+de\s+la\s+emisi[oó]n', r'Divisa\b',
                           r'Divisa\s+de\s+denominaci[oó]n',
                           r'Moneda\b'], 'currency', ver='1.1'),
    FieldSpec('issue_date', [r'\bIssue\s+Date\b', r'Fecha\s+de\s+emisi',
                             r'Fecha\s+de\s+[Dd]esembolso'], 'date',
              ver='1.1'),
    FieldSpec('maturity', [r'\bMaturity\s+Date\b', r'Fecha\s+de\s+vencimiento',
                           r'Fecha\s+de\s+amortizaci[oó]n\s+final',
                           r'Fecha\s+de\s+[Aa]mortizaci[oó]n\b'
                           r'(?!\s*[:-]?\s*anticipada)',
                           r'Vencimiento\b'], 'date', ver='1.1'),
    FieldSpec('denomination', [r'Specified\s+Denomination',
                               r'Denominaci[oó]n\s+unitaria',
                               r'Valor\s+nominal\s+unitario',
                               r'Importe\s+unitario\s+de\s+los\s+[Vv]alores',
                               r'Importe\s+nominal\s+unitario\s+de\s+los\s+'
                               r'[Vv]alores',
                               r'Nominal\s+unitario'], 'money', ver='1.1'),
    FieldSpec('issued_amount', [r'Aggregate\s+(?:Principal|Nominal)\s+Amount(?:\s+of\s+(?:the\s+)?Notes)?',
                                r'Aggregate\s+Amount',
                                r'Importe\s+(?:nominal\s+)?total\s+de\s+la\s+emisi[oó]n',
                                r'Importe\s+total\s+(?:nominal|efectivo)\s+de\s+la\s+emisi[oó]n',
                                r'Importe\s+nominal\s+y\s+efectivo\s+de\s+la\s+emisi[oó]n',
                                r'Importe\s+nominal\s+y\s+efectivo\s+de\s+los\s+[Vv]alores',
                                r'Importe\s+de\s+la\s+[Ee]misi[oó]n',
                                r'por\s+un\s+importe\s+(?:nominal\s+)?(?:total\s+)?de'],
              'money', ver='1.1'),
    FieldSpec('coupon_type', [r'Interest\s+Basis', r'Tipo\s+de\s+inter[eé]s\b'],
              'text', multi=True),
    FieldSpec('coupon_rate', [r'Rate\s+of\s+Interest\b',
                              r'Interest\s+Basis',
                              r'Tipo\s+de\s+inter[eé]s\s+nominal',
                              r'Tipo\s+de\s+inter[eé]s\s+inicial',
                              r'Fixed\s+Coupon\s+Rate',
                              r'Tipo\s+de\s+inter[eé]s\b(?!\s*(?:fijo|variable|inicial|m[ií]nimo|m[aá]ximo|indexado|de\s+demora))'],
              'percent', ver='1.2', multi=True),
    FieldSpec('benchmark', [r'Floating\s+Rate\s+Option',
                            r'Nombre\s+y\s+descripci[oó]n\s+del\s+Tipo\s+de\s+Referencia',
                            r'Tipo\s+de\s+referencia',
                            r'[ÍI]ndice\s+de\s+referencia',
                            r'Reset\s+Reference\s+Rate',
                            r'Reference\s+Rate\b',
                            r'Tipo\s+de\s+inter[eé]s\s*:',
                            r'Tipo\s+de\s+[Ss]ubyacente',
                            r'Nombre\s+y\s+descripci[oó]n\s+del\s+[Ss]ubyacente',
                            r'\bEURIBOR\b', r'€STR\b'], 'benchmark', ver='1.1',
              multi=True),
    FieldSpec('spread', [r'First\s+Margin', r'Subsequent\s+Margin',
                         r'\bMargin[s]?\s*:', r'\bSpread\b',
                         r'Margen\s*(?:sobre\s+el\s+tipo\s+de\s+referencia)?\s*:',
                         r'Tipo\s+de\s+inter[eé]s\s*:',
                         r'Tipo\s+de\s+[Rr]eferencia',
                         r'Nombre\s+y\s+descripci[oó]n\s+del\s+Tipo\s+de\s+Referencia'],
              'spread', ver='1.1', multi=True),
    FieldSpec('payment_frequency', [r'Interest\s+Payment\s+Date\(s\)?',
                                    r'Fechas?\s+de\s+pago\s+de\s+(?:los\s+)?(?:intereses|cupones)',
                                    r'Fecha\s+de\s+[Pp]ago\b',
                                    r'Periodo\s+de\s+devengo\s+de\s+los\s+intereses'],
              'frequency', ver='1.1', multi=True),
    FieldSpec('day_count', [r'Day\s+Count\s+Fraction', r'Base\s+de\s+c[aá]lculo',
                            r'Day\s+Count\s+Basis'], 'text'),
    FieldSpec('call_dates', [r'Optional\s+Redemption\s+Dates?',
                             r'Early\s+Redemption\s+Date\(s\)',
                             r'Call\s+Option\s+Date', r'Call\s+Option\s*:',
                             r'Issuer\s+Call\s+Option', r'Issuer\s+Call\b',
                             r'Issuer\s+Clean-?Up\s+Call', r'Clean-?Up\s+Call',
                             r'Put/Call\s+Options?',
                             r'Residual\s+Maturity\s+Call\s+Option',
                             r'Opci[oó]n(?:es)?\s+de\s+amortizaci[oó]n(?:\s+anticipada)?'
                             r'(?:\s+o\s+cancelaci[oó]n(?:\s+anticipada)?)?'
                             r'(?:\s+para\s+el\s+Emisor)?',
                             r'Opci[oó]n\s+(?:del?\s+)?Emisor',
                             r'Amortizaci[oó]n\s+anticipada\s+(?:por|para)\s+el\s+[Ee]misor'],
              'dates_or_text', ver='1.2', multi=True),
    FieldSpec('business_day_convention', [r'Business\s+Day\s+Convention',
                                          r'Convenci[oó]n\s+(?:del?\s+)?d[ií]a[s]?\s+h[aá]bil(?:es)?'],
              'text', ver='1.1',
              value_rx=(r'(?:Modified\s+)?Following\s+Business\s+Day\s+Convention|'
                        r'Preceding\s+Business\s+Day\s+Convention|'
                        r'FRN\s+Convention|'
                        r'Convenci[oó]n\s+del?\s+Siguiente\s+D[ií]a\s+H[aá]bil|'
                        r'Convenci[oó]n\s+del?\s+D[ií]a\s+H[aá]bil\s+(?:Anterior|Precedente|'
                        r'Siguiente\s+Modificada?)|'
                        r'Siguiente\s+D[ií]a\s+H[aá]bil\s*\(?\s*Following\s+Business\s+Day'
                        r'\s+Convention\s*\)?'),
              multi=True),
    # ---------- segunda ola (G0-C.1, deep-dev) ----------
    FieldSpec('put_dates', [r'Securityholder\s+Put\s+Option',
                            r'Noteholder\s+Put\b',
                            r'Change\s+of\s+Control\s+Put\s+Option',
                            r'Put\s+Option\s*:',
                            r'Opci[oó]n\s+(?:del?\s+)?Inversor',
                            r'Amortizaci[oó]n\s+anticipada\s+por\s+el\s+inversor',
                            r'Opci[oó]n\s+de\s+(?:reembolso|venta)\s+anticipada'],
              'dates_or_text', ver='1.1', multi=True),
    FieldSpec('reset_dates', [r'First\s+Reset\s+Date', r'Second\s+Reset\s+Date',
                              r'Subsequent\s+Reset\s+Date',
                              r'Reset\s+Note\s+Provisions',
                              r'Fecha[s]?\s+de\s+revisi[oó]n',
                              r'Fecha\s+de\s+[Rr]eset',
                              r'Fecha\s+de\s+modificaci[oó]n\s+del\s+tipo',
                              r'\bReset\s+Date\b'],
              'dates_or_text', ver='1.1', multi=True),
    FieldSpec('fixing_rules', [r'Fechas?\s+de\s+determinaci[oó]n\s+del\s+tipo\s+de\s+inter[eé]s(?:\s+aplicable)?',
                               r'Fechas?\s+de\s+[Dd]eterminaci[oó]n\s+de\s+Intereses',
                               r'Fecha\s+de\s+Determinaci[oó]n\s+del\s+Tipo\s+de\s+Inter[eé]s',
                               r'Momento\s+de\s+Determinaci[oó]n',
                               r'Pantalla\s+Relevante',
                               r'Procedimiento\s+de\s+publicaci[oó]n\s+de\s+(?:la\s+)?fijaci[oó]n(?:\s+de\s+los\s+nuevos\s+tipos\s+de\s+inter[eé]s)?',
                               r'Reset\s+Determination\s+(?:Time|Date)',
                               r'Relevant\s+Screen\s+Page',
                               r'Screen\s+Rate\s+Determination',
                               r'Determinaci[oó]n\s+ISDA',
                               r'Determinaci[oó]n\s+por\s+referencia\s+al\s+Tipo\s+de\s+Pantalla',
                               r'Determination\s+Date\(s\)'],
              'text', ver='1.1', multi=True),
    FieldSpec('ranking', [r'Status\s+of\s+the\s+(?:Notes|Instruments|Valores)',
                          r'Estatus\s+de\s+los\s+[Vv]alores',
                          r'Rango\s+de\s+los\s+[Vv]alores',
                          r'Jerarqu[ií]a'], 'ranking'),
    FieldSpec('subordination', [r'Status\s+of\s+the\s+(?:Notes|Instruments|Valores)',
                                r'Estatus\s+de\s+los\s+[Vv]alores',
                                r'Categor[ií]a\s+de\s+los\s+[Vv]alores',
                                r'Subordinaci[oó]n'], 'subordination'),
    FieldSpec('redemption_formula',
              [r'Redemption\s*/?\s*Payment\s+Basis', r'Redemption\s+Basis',
               r'Final\s+Redemption\s+Amount',
               r'Maturity\s+Redemption\s+Amount',
               r'Sistema\s+de\s+amortizaci[oó]n',
               r'Precio\s+de\s+[aA]mortizaci[oó]n\s+[fF]inal',
               r'Fecha\s+de\s+amortizaci[oó]n\s+final(?:\s+y\s+sistema\s+de\s+amortizaci[oó]n)?',
               r'Fecha\s+de\s+amortizaci[oó]n\s+a\s+vencimiento'],
              'text', multi=True),
    FieldSpec('underlying', [r'Reference\s+Item\(s\)',
                             r'Nombre\s+y\s+descripci[oó]n\s+del\s+Subyacente',
                             r'Descripci[oó]n\s+del\s+[Ss]ubyacente',
                             r'Tipo\s+de\s+[Ss]ubyacente',
                             r'\bIndex\s*:', r'\bUnderlying\b'], 'text',
              multi=True),
    FieldSpec('barrier', [r'Barrera\s+de\s+Cup[oó]n', r'Coupon\s+Barrier',
                          r'Knock-in\s+Barrier', r'Knock-out\s+Barrier',
                          r'Automatic\s+Early\s+Redemption\s+Trigger',
                          r'\bBarrier\b'], 'text_or_percent', multi=True),
    FieldSpec('autocall', [r'Automatic\s+Early\s+Redemption\s*:',
                           r'Estructura\s+de\s+Cancelaci[oó]n\s+Anticipada',
                           r'\bAutocall\b'], 'applicability', multi=True),
    FieldSpec('observation_dates',
              [r'Fecha[s]?\s+de\s+Observaci[oó]n\s+(?:Inicial|Final)?',
               r'Observation\s+Date\(s\)', r'Coupon\s+Valuation\s+Date',
               r'Redemption\s+Valuation\s+Date',
               r'Knock-in\s+Determination\s+Day', r'Strike\s+Date',
               r'Valuation\s+Date\(s\)'], 'dates_or_text', multi=True),
    FieldSpec('settlement_type',
              [r'Liquidaci[oó]n\s+de\s+los\s+valores(?:\s+y\s+llevanza\s+del\s+registro\s+de\s+anotaciones\s+en\s+cuenta)?',
               r'Sistema\s+de\s+Compensaci[oó]n\s+y\s+Liquidaci[oó]n',
               r'Forma\s+de\s+liquidaci[oó]n', r'\bDelivery\b',
               r'Variation\s+of\s+Settlement',
               r'Settlement\s+(?:Exchange\s+Rate\s+)?Provisions'], 'text',
              multi=True),
    FieldSpec('participation', [r'Participation\s+Rate', r'\bParticipation\b',
                                r'Participaci[oó]n'], 'text_or_percent'),
    FieldSpec('cap', [r'Maximum\s+Interest\s+Rate', r'Maximum\s+Rate',
                      r'Tipo\s+de\s+inter[eé]s\s+m[aá]ximo',
                      r'Cap\s+Rate', r'\bCap\s*[:=]'], 'text_or_percent',
              ver='1.1'),
    FieldSpec('strike', [r'Strike\s+(?:Price|Level)', r'Initial\s+Strike',
                         r'Precio\s+de\s+ejercicio'], 'text_or_percent'),
]

EXTRACTORS = [Extractor(f'EXTRACT_{s.field.upper()}', s.ver, s)
              for s in FIELD_SPECS]


def extract_all(view: NormalizedDocumentView, doc_role: str = 'final_terms'
                ) -> list[TermObservation]:
    out = []
    for ex in EXTRACTORS:
        if doc_role not in ex.spec.doc_roles and '*' not in ex.spec.doc_roles:
            continue
        out.append(extract_field(view, ex.spec, ex.extractor_id, ex.version))
    return out
