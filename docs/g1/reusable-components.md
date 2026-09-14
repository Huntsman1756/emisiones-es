# G1-A0 — Reusable Components

Inventario de componentes/patrones reutilizables ordenados por impacto
esperado sobre los fallos G0. Ningún componente se integra todavía — esto es
el mapa de decisión para el desarrollo G1.

## Arquitectura (F7 — impacto mayor)

| Componente | Origen | Licencia | Forma de uso |
|---|---|---|---|
| family dispatcher: signatures acotadas + data anchors + UNKNOWN | vc-statement-parser | MIT | PORT_PATTERN — `classify_document_role()` con anchors obligatorios |
| Extractor interface `supports()/extract()` → modelo tipado | vc-statement-parser | MIT | PORT_PATTERN — un extractor por `document_role`, no specs universales |
| invariant verification → ValidationReport | vc-statement-parser | MIT | PORT_PATTERN — invariantes de términos contractuales |
| probe → route por text_coverage → DocumentIR con `source_block_id` | contract-rag | Apache-2.0 | PORT_PATTERN — provenance por bloque |
| eval taxonomy omission/invention + null inference + constraints | termsheet-extraction-eval | MIT | PORT_PATTERN — scoring G1 NA/ABSENT/OCR-gap |

## Localización + extracción (F3 — recall)

| Componente | Origen | Licencia | Forma de uso |
|---|---|---|---|
| grep-first scan → clustering densidad → sección formal | sovereign-prospectus-corpus | MIT | PORT_PATTERN — localizar antes de extraer |
| verbatim verify `exact_quote in raw_text` | sovereign-prospectus-corpus | MIT | PORT_PATTERN — gate de evidencia ya alineado con nuestro contrato |
| classify_table → extractor key-value tipado + catch-all | edgartools `_424b_tables` | MIT | PORT_PATTERN — tablas de términos CNMV |
| FinTOC title/TOC detection (track ES, XGBoost) | dedoc | Apache-2.0 | ADOPT_EVAL — estructura de secciones en prospectos largos; verificar licencia de pesos |

## Linkage / document graph (F1, F2)

| Componente | Origen | Licencia | Forma de uso |
|---|---|---|---|
| family-first-then-temporal (familia por identificador explícito, orden temporal solo dentro) | edgartools `ShelfLifecycle` | MIT | PORT_PATTERN — núcleo del fix S4 |
| generations / re-registration / continuity / gap-flag | edgartools | MIT | PORT_PATTERN — sucesión de programas como generaciones declaradas |
| signal-cascade classifier con signals+confidence auditables | edgartools `_424b_classifier` | MIT | PORT_PATTERN — document_role classification |

## Semántica canónica (F4, F5, F6)

| Componente | Origen | Licencia | Forma de uso |
|---|---|---|---|
| DayCountFractionEnum (displayName + cita ISDA por valor) | FINOS CDM | Apache-2.0/CC* | ADOPT como tabla de datos canónica — id + aliases + ref |
| `Callability{price,Call|Put,date}` + Schedule | QuantLib | BSD-3 | PORT_PATTERN — modelo canónico call/put |
| barrier roles: autocall_trigger / coupon_barrier / protection_barrier + pdi_strike + memory | structured-products-toolkit | MIT | REFERENCE — modelo canónico + fixtures/oracles |
| convenciones day-count (cross-check) | Strata, QuantLib | Apache-2.0/BSD-3 | REFERENCE — validación de tabla |

\* verificar licencia por componente antes de vendor.

## Lo que sigue siendo exclusivamente CUSTOM (CNMV)

```text
- identificadores de familia CNMV (nº registro folleto base / programa)
- evidencia de sucesión declarada en fuente española
- vocabularios de labels ES/EN por document_role
- specs de formatos CNMV: CCFF, securities note, multi-tramo
- adquisición/registro CNMV (ya construido en G0-B)
- scoring contract + holdout discipline (ya construido)
```

## Reducción esperada de código custom

```text
dispatcher + extractor interface + verify     ~500-700 LOC evitadas
locate-then-extract + verbatim verify         ~300-400 LOC
signal cascade + table classifiers            ~300-400 LOC
day-count canonical table + callability model ~200-300 LOC
eval layer (taxonomy + null inference)        ~300-400 LOC
--------------------------------------------
total                                        ~1600-2200 LOC de diseño+iteración
```

El código original de Emisiones ES queda donde debe: **semántica/identidad
CNMV y adaptación al régimen español**. Todo lo demás tiene justificación
documentada antes de ser CUSTOM.

## Riesgos / pendientes

1. **dedoc**: licencia de pesos XGBoost en HF hub + nueva dependencia
   xgboost/pandas → evaluar en G1 dev antes de ADOPT.
2. **CDM**: confirmar licencia exacta del enum antes de vendor la tabla.
3. **dedoc/FinTOC produce estructura, no valores** — la extracción factual
   sigue siendo determinista; el clasificador vive en la capa de parsing
   (misma categoría que RapidOCR/TableFormer).
4. Ningún upstream resuelve la **evidencia de sucesión CNMV** — es la parte
   estrictamente española de F1.
