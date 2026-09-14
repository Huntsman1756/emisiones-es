# G1-A0 — Upstream Audit

Audit de candidatos OSS contra los fallos G0. Criterio: inspección de
código/tests/licencia real — no stars ni READMEs. Datos estructurados en
`g1/research/candidates.json`; decisiones por fallo en `decisions.json`.

## Resumen de decisiones

```text
ADOPT        1   (CDM DayCountFractionEnum como tabla canónica de datos)
ADOPT_EVAL   1   (dedoc FintocStructureExtractor — evaluar en G1 dev)
FORK         0
WRAP         0
PORT_PATTERN 8
REFERENCE    5
REJECT       2   (LLM factual extraction — incompatible con el contrato)
```

## Auditoría por repositorio

### dgunning/edgartools — MIT @ abe4434 — PORT_PATTERN

El proyecto OSS más relevante encontrado. `ShelfLifecycle` (571 LOC) +
pipeline completo 424B con 847 LOC de tests de regresión.

- **Linkage**: la relación se establece por `file_number` explícito;
  `_generations`/`continuity`/`has_registration_gap` modelan re-registration
  y gaps **sin forzar** relaciones. Patrón directamente aplicable a F1.
- **Clasificación**: `_424b_classifier` — cascada de señales auditables con
  confidence; `_424b_tables` — `classify_table` → extractor por clase con
  catch-all honesto.
- **Riesgo**: ninguna dependencia directa; patrones limpios. SEC-especificidad
  contenida en vocabularios (forms, file_number, Rule 415).

### Teal-Insights/sovereign-prospectus-corpus — MIT @ 2923a18 — PORT_PATTERN

`clause_extractor.py` (587 LOC): grep-first → clustering de densidad →
verbatim extract → `verify_extraction` (`exact_quote in raw_pdf_text`).
Resuelve la mitad de nuestros FN: **localizar antes de extraer**. Identidad
estable `{source}__{native_id}`, snapshots, atomic writes — alineado con
nuestra disciplina de freeze. Su propio CLAUDE.md marca los scripts como
reference-only-rewrite: coherente con PORT_PATTERN.

### qiangweihewu/contract-rag — Apache-2.0 @ bc3cfd6 — PORT_PATTERN

`parse/router.py`: probe → route por `text_coverage` → `DocumentIR` común
con `source_block_id` por bloque y remap al segmentar. Eval
`fincritical/coverage/degrade`: taxonomía omission vs invention con
calibración de confianza OCR — el vocabulario correcto para nuestro scoring.
Negative results documentados: disciplina compatible.

### VenturFlow/vc-statement-parser — MIT @ 29f8004 — PORT_PATTERN

El patrón arquitectónico más aplicable a G1: `dispatcher` (firmas en header
acotado + `REQUIRED_DATA_ANCHORS` que distinguen mención de página real +
`UNKNOWN`) → `Extractor` ABC (`supports`/`extract`) → modelo tipado →
`verification.py` con invariantes aritméticos, tolerancias explícitas y
`ValidationReport`. ~250 LOC de patrón directamente portable.

### ispras/dedoc — Apache-2.0 @ 40dde1b — ADOPT_EVAL

`FintocStructureExtractor` = implementación del ganador FinTOC-2022 con track
**español**: title detection + TOC generation para prospectos financieros en
PDF. Pesos XGBoost descargados de HF hub en runtime. Encaja en la capa de
parsing (como RapidOCR/TableFormer) — no toca la extracción factual
determinista. Pendiente antes de ADOPT: licencia de los pesos, dependencia
xgboost+pandas, evaluación sobre folletos CNMV en G1 dev.

### inherent-vice/termsheet-extraction-eval — MIT @ a95abdd — PORT_PATTERN

Eval harness de producción (89 campos × 410 derivados, 94.5% field acc):
taxonomy `MATCH/MISMATCH/OCR_NULL/NOT_FOUND`, comparadores type-aware,
`null_inference` con categorías A–C (defaults por regla / siblings /
ausencia genuina), constraint engine cruzado. El matiz OCR_NULL-vs-ausencia
es exactamente lo que nuestro scoring NA/ABSENT necesita.

### mattkorman/structured-products-toolkit — MIT @ ddb83d7 — REFERENCE

`AutocallNote`: tres barrier roles distintos (autocall_trigger /
coupon_barrier / protection_barrier), `pdi_strike`, memory, observation
schedule. Demuestra que nuestro `barrier` único es un defecto de modelo.
Uso: semántica canónica + generador de fixtures/oracles, no extractor.

### lballabio/QuantLib — BSD-3 — PORT_PATTERN + REFERENCE

`Callability{price, Type{Call,Put}, date}` + `CallabilitySchedule` = forma
canónica para call/put schedules (más rica que `list[date]`). DayCounters
(ISMA/ISDA/AFB…) para validación semántica. C++ — portar la forma, no el
código.

### OpenGamma/Strata — Apache-2.0 — REFERENCE

`StandardDayCounts` completo — cross-check de la tabla canónica CDM.

### finos/common-domain-model — Apache-2.0/CC — ADOPT (tabla) + REFERENCE

`DayCountFractionEnum` con `displayName` + cita ISDA por valor. Vocabulario
canónico con respaldo institucional. Verificar licencia por componente antes
de vendor la tabla.

### hoholebg/fixed-income-doc-intelligence — SIN LICENCIA — REFERENCE

Badge MIT en README ≠ LICENSE file. Además el pipeline anunciado (Docling +
hybrid matching) **no está en el repo** (~312 LOC de scripts de estados
financieros franceses). REFERENCE solo para la idea arquitectónica.

### digital-asset/daml-finance — Apache-2.0 — REFERENCE

Segunda fuente de semántica callable; no inspeccionado a fondo porque
QuantLib ya resolvió la estructura canónica.

### rundimeco/daniel_fintoc2019 — REFERENCE

Feature set de title detection FinTOC-2019; superado por dedoc (ganador 2022,
ES, mantenido).

### Rechazados por incompatibilidad de invariante

- `sburstein/cat-bond-pricer` — LLM (Claude) structured extraction.
- `ashish620/bond-data-intelligence-platform` — RAG + LLM grounding.

Ambos romperían `no LLM factual extraction` y provenance verbatim. Se
registran como evidencia de que el enfoque determinista sigue siendo el
diferenciador.

## Breadth de búsqueda

Combinaciones ejecutadas: `bond prospectus parser`, `final terms parser`,
`term sheet parser`, `424B2 parser`, `prospectus lifecycle`, `FinTOC`,
`document provenance`, `structured note parser`. Candidatos adicionales
(LLM-based, dashboards, pricing) descartados por invariante o por
irrelevancia para los fallos G0. Repos archivados aceptados como REFERENCE.

## Bloqueadores de licencia

```text
fixed-income-doc-intelligence   sin LICENSE → REFERENCE (no copy/fork/vendor)
dedoc pesos XGBoost             verificar licencia en HF hub antes de ADOPT
CDM                             verificar licencia por componente antes de vendor
daml-finance                    confirmar Apache-2.0 si se usa algo más que reference
```
