# Modelo conceptual mínimo (G0)

Borrador de dominio — no es el modelo de producción. Solo lo necesario para
los gates G0-B…G0-G.

## Entidades

```text
Issuer                  persona jurídica emisora (LEI, NIF, nombre registral)
Security                instrumento financiero canónico (objeto central)
Programme               programa de emisión (EMTN, cédulas, bonos…)
Document                artefacto documental observado (PDF, registro)
DocumentRelation        arista tipada entre Documents
Issuance                emisión concreta bajo un Programme
Venue                   infraestructura/mercado (ver venue-model.md)
InstrumentVenue         relación instrumento↔venue con rol y fechas
SettlementArrangement   cómo se liquida/registra (ARCO, DLT-TSS, …)
TermObservation         observación de un término contractual en una fuente
SourceObservation       hecho observado en una fuente primaria
Conflict                discrepancia preservada entre observaciones
```

## Identificadores cualificados (nunca clave universal)

```text
identifier_type   ISIN | LEI | NIF | CNMV_REG_NO | CNMV_CCFF_ID | DOC_ID | FIGI…
identifier_value  valor
source            quién lo afirma
valid_from/valid_to
```

## Grafo documental

Tipos de nodo: `PROGRAMME | BASE_PROSPECTUS | SUPPLEMENT | FINAL_TERMS |
CORRECTION | REDEPOSIT | ADMISSION | SECURITY`

Aristas: `ISSUED_UNDER | SUPPLEMENTS | CORRECTS | REPLACES | RELATES_TO |
DEFINES_TERMS_FOR | ADMISSION_OF`

Estados de enlace: `EXACT_LINK | NO_LINK | AMBIGUOUS`.
`AMBIGUOUS` nunca se promociona a enlace factual automáticamente.

## TermObservation (provenance a nivel de campo)

```text
field            nombre canónico (issue_date, coupon_rate, call_dates…)
value            valor normalizado
status           OBSERVED | DERIVED | INFERRED | CONFLICT | MISSING
source, source_record_id, document_id, observed_at, snapshot_hash
page, bbox, span/text_evidence   (cuando existan, vía Docling prov)
extractor, extractor_version
```

## Mapping semántico (a construir como artefacto)

```text
concepto CNMV → concepto canónico Emisiones ES → concepto FINOS CDM →
concepto FIRDS/ESAP
```

Tabla semilla (filas a completar durante G0-C/D):

| CNMV / folleto | Canónico | CDM (aprox.) | FIRDS (RTS 23) |
|---|---|---|---|
| Fecha de emisión | `issue_date` | `Product.issuanceDate` | — (no directo) |
| Vencimiento | `maturity` | `maturityDate` | `Maturity date` |
| Divisa | `currency` | `SettlementCurrency` | `Currency of nominal` |
| Nominal por unidad | `denomination` | `denomination` | `Nominal value per unit` |
| Importe emitido | `issued_amount` | `issuanceAmount` | `Total issued nominal` |
| Tipo de cupón | `coupon_type` | `InterestRatePayout.type` | `Fixed rate` flag |
| Tipo fijo | `coupon_rate` | `fixedRate.rate` | `Fixed rate` |
| Índice/benchmark | `benchmark` | `floatingRateOption` | `Underlying index` |
| Margen | `spread` | `spread` | `Base point spread` |
| Día de cómputo | `day_count` | `dayCountFraction` | — ausente |
| Ajuste días hábiles | `business_day_convention` | `businessDayConvention` | — ausente |
| Call schedule | `call_dates` | `callFeature` | — ausente |
| Put schedule | `put_dates` | `putFeature` | — ausente |
| Amortización/redención | `redemption_formula` | `redemptionPayout` | — ausente |
| Rango/subordinación | `ranking/subordination` | `seniority` | `Seniority (4 valores)` |
| Barrera/strike/autocall… | `barrier`, `strike`, `autocall`, `observation_dates` | `OptionPayout`/`observation` | — ausente |
