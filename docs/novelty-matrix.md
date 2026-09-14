# Novelty matrix — valor diferencial frente a superficies estructuradas

Clasificación de cada campo canónico frente a **FIRDS** (RTS 23),
**metadata ESAP** y **superficies estructuradas CNMV**. Sin datos
comerciales BME. Machine-readable: `g0/manifests/novelty-field-map.json`.

Estados:

- `STRUCTURED_UPSTREAM` — ya disponible estructurado upstream.
- `PARTIALLY_STRUCTURED` — existe una versión parcial/agregada;
  el detalle contractual vive en el documento.
- `DOCUMENT_ONLY` — solo existe en el documento fuente.
- `NOT_DETERMINED` — no determinado en G0.

## Campos

| campo | FIRDS | ESAP | CNMV struct | novelty |
|---|---|---|---|---|
| isin | STRUCTURED | STRUCTURED | STRUCTURED | upstream |
| currency | STRUCTURED | n.d. | STRUCTURED | upstream |
| issue_date | PARTIAL | PARTIAL | PARTIAL | partial |
| maturity | STRUCTURED | n.d. | PARTIAL | upstream |
| denomination | PARTIAL | n.d. | n.d. | partial |
| issued_amount | STRUCTURED | PARTIAL | STRUCTURED | upstream |
| coupon_type | PARTIAL | n.d. | PARTIAL | partial |
| coupon_rate | PARTIAL | n.d. | PARTIAL | partial |
| benchmark | PARTIAL | n.d. | n.d. | partial |
| spread | PARTIAL | n.d. | n.d. | partial |
| payment_frequency | — | — | — | DOCUMENT_ONLY |
| day_count | — | — | — | DOCUMENT_ONLY |
| call_dates | — | — | — | DOCUMENT_ONLY |
| put_dates | — | — | — | DOCUMENT_ONLY |
| business_day_convention | — | — | — | DOCUMENT_ONLY |
| reset_dates | — | — | — | DOCUMENT_ONLY |
| fixing_rules | — | — | — | DOCUMENT_ONLY |
| ranking | PARTIAL | n.d. | n.d. | partial |
| subordination | PARTIAL | n.d. | n.d. | partial |
| redemption_formula | — | — | — | DOCUMENT_ONLY |
| underlying | PARTIAL | n.d. | n.d. | partial |
| barrier | — | — | — | DOCUMENT_ONLY |
| autocall | — | — | — | DOCUMENT_ONLY |
| observation_dates | — | — | — | DOCUMENT_ONLY |
| settlement_type | PARTIAL | n.d. | n.d. | partial |
| participation | — | — | — | DOCUMENT_ONLY |
| cap | — | — | — | DOCUMENT_ONLY |
| strike | — | — | — | DOCUMENT_ONLY |
| document_lineage | — | PARTIAL | PARTIAL | DOCUMENT_ONLY |

## Base factual (G0-A)

FIRDS/RTS 23 reporta: ISIN, FISN, CFI, LEI, MIC, fechas de solicitud /
aprobación / admisión, nominal total, vencimiento, divisa, nominal por
unidad, flag fijo/flotante, índice+spread (bps) en flotantes, seniority
grueso (SNDB/MZZD/SBOD/JUND).

FIRDS **no** reporta: calendario call/put, day-count, frecuencia de
pago, reset/fixing, barreras, autocall, fórmulas de amortización,
convenciones de día hábil, subyacentes de estructurados, ni relaciones
documentales.

ESAP (portal público ~2027) aportará metadata documental, no términos
contractuales a nivel de campo.

CNMV estructurado (filas CCFF/admisión) aporta identidad, importe y
fechas de registro; no términos a nivel de campo ni grafo documental.

## Lectura

La tesis OSS_DELTA se sostiene sobre los campos `DOCUMENT_ONLY`:
15 de 29 campos canónicos (incl. `document_lineage`) no existen en
ninguna superficie estructurada upstream. Los campos `PARTIALLY_`
aportan valor cuando el detalle difiere del agregado upstream
(p.ej. benchmark por tramo, margins escalonados, tiers precisos).
