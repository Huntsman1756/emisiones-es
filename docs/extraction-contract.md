# Contrato de extracción (G0-C)

## Principio

Toda observación contractual es un `TermObservation` con:

```text
field, value?, status, raw_lexeme, evidence[],
extractor, extractor_version
```

**Sin ancla semántica no hay promoción.** Un número financieramente
plausible no se acepta salvo que un label contractual lo soporte.

## Pipeline

```text
DoclingDocument
  -> NormalizedDocumentView (adaptador; conserva prov/page/bbox)
  -> Estrategias deterministas por campo:
       isin_scan      (auto-ancla, ISIN standalone/embebido)
       label_value    (ancla ES/EN -> valor inline, derecha, debajo,
                       celda de tabla vecina, label partido en 2 líneas)
       coupon_classifier (clasificador; 'Rate Reset'/'Variable' -> CONFLICT
                          cuando el documento fija regímenes múltiples)
  -> normalizadores deterministas (números ES/EN, fechas ES/EN, %, divisa,
     importe con divisa)
```

Estados: `DERIVED` (normalizado reproducible), `CONFLICT` (valores
incompatibles conservados, p.ej. cupón fijo→variable por prórroga en
cédulas), `MISSING` (ausencia conocida — nunca se rellena por
inferencia).

## Campos de primera ola

`isin, currency, issue_date, maturity, denomination, issued_amount,
coupon_type, coupon_rate, benchmark, spread, payment_frequency,
day_count, call_dates, business_day_convention`

Anclas bilingües ES/EN con prefijo numérico ICMA opcional
(`(i)`, `(xxii)`, `45.`, `b)`). Guardas anti-fuga: números ICMA no
cuentan como valor; frases verbales ("is", "are", "es", "son") tras el
ancla no son valor.

## Evidencia

Cada valor DERIVED lleva `EvidencePointer` con source, record key,
snapshot SHA-256, página y bbox Docling. Ver
`src/emissions_es/extraction/extractors.py` (registry `EXTRACTORS`).
