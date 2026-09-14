# G1-A0 — OSS Failure Map

Regla aplicada: **cada fallo G0 tiene un repo audit antes de recibir código
CUSTOM**. Inspección sobre HEAD clonado (commits en `g1/research/candidates.json`).

## F1 — Linkage S4 programme succession (25 fails, MISSING_EXPLICIT_REFERENCE)

**Root cause**: la fila CNMV no declara la sucesión; resolverla por precedencia
temporal es *inferir* una relación que la fuente no declara.

**Upstream**: `dgunning/edgartools` — `ShelfLifecycle` + `related_filings`.

**Evidencia del código** (`edgar/offerings/prospectus/`):

- La familia se establece por **identificador explícito**: `file_number` leído
  de la cover/SGML header (`document.py:412`, `registration_s1.py:382`),
  nunca por proximidad temporal.
- `ShelfLifecycle` ordena temporalmente **dentro** de la familia ya
  relacionada (`takedowns` sort por `(filing_date, accession_no)`, l.179).
- Re-registration = `_generations` (eventos de efectividad discretos);
  `continuity` marca `'lapsed'` cuando una generación llega tarde;
  `has_registration_gap` señala calidad de dato **en vez de forzar** una
  relación continua.
- Distinción de roles por vocabulario de forms: `_SHELF_BASE_FORMS`,
  `_TAKEDOWN_FORMS`, `RW`/`RW WD`/`AW` con semántica de anulación.

**Decisión: PORT_PATTERN.** Transferible: family-first-then-temporal,
generations/re-registration, gap-flag, orden determinista con tiebreak.
SEC-específico (no portar): `file_number`, `EFFECT`, ASR, Rule 415.

**CUSTOM restante**: identificador de familia CNMV (nº registro folleto base /
id de programa); evidencia de sucesión *declarada* (campo CNMV o texto del
propio folleto "sustituye a..."); bajo el modelo G1, S4 sin evidencia
explícita → `REVIEW_REQUIRED`, no `AUTO_LINKED` ni enlace forzado.

## F2 — S7/S9 document role (10 fails, RULE_DEFECT)

**Root cause**: superficie de adquisición usada como proxy del rol; sin
anchors que distingan "la página menciona X" de "la página ES X".

**Upstreams**: edgartools `_424b_classifier` · vc-statement-parser
`dispatcher` · dedoc `FintocStructureExtractor`.

**Evidencia**:

- `_424b_classifier.py`: cascada de señales débiles por candidato con
  `signals[]` + `confidence` auditables; form type como prior duro;
  fallback estructural (XBRL security type) solo cuando la cascada de texto
  es inconcluyente.
- `vc-statement-parser/dispatcher.py`: firmas restringidas a ~1500 chars de
  header + `_REQUIRED_DATA_ANCHORS` por familia (la cabecera sola no basta:
  exige tokens estructurales que solo aparecen en la página real) +
  `per_page_text` para docs embebidos + fallback `UNKNOWN`.
- dedoc FinTOC: title detection + TOC para prospectos EN/FR/**ES**
  (XGBoost entrenado, ganador FinTOC-2022 modificado).

**Decisión: PORT_PATTERN ×2 + ADOPT_EVAL (dedoc).**

**CUSTOM restante**: firmas y anchors por rol CNMV (ES/EN); la taxonomía
`acquisition_surface/document_role/scope_role` ya está en AMEND-1.

## F3 — coupon_rate (prec 0.9333 < 0.95, recall 0.409)

**Root cause**: doble — fallo de **localización** (campo en zona no recorrida
o formato desconocido) y promoción de lexema sin contexto de label.

**Upstreams**: edgartools `_424b_tables` · sovereign-prospectus-corpus
`clause_extractor`.

**Evidencia**:

- `_424b_tables/classifiers.py` → `extractors.py`: clasificar la tabla por
  keywords (`_is_key_terms`, `_is_pricing_table`...) y solo entonces extraer
  key-value; bullets stripped; `value = last cell`; catch-all
  `additional_terms` honesto en `extract_structured_note_terms`.
- `clause_extractor.py`: `grep_first_scan` → `identify_clause_sections`
  (clustering de páginas con matches densos, ventana ±2, elige el cluster con
  más matches = definición formal, no mención) → extract verbatim →
  **`verify_extraction`: `assert exact_quote in raw_pdf_text`** con
  normalización de whitespace.

**Decisión: PORT_PATTERN ×2** — separar *localizar región* de *extraer valor*,
con verificación verbatim obligatoria.

**CUSTOM restante**: vocabulario de labels CNMV ES/EN; specs para formato
securities-note y multi-tramo (X27/X28).

## F4 — day_count (prec 0.9375 < 0.95)

**Root cause**: (a) `'1/1'` promovido sin contexto — **es una convención ISDA
real** (`CDM _1_1`), el fallo fue de contexto no de lexema; (b) normalización
sin vocabulario canónico.

**Upstreams**: FINOS CDM `DayCountFractionEnum` · QuantLib · Strata.

**Evidencia**: `base-datetime-daycount-enum.rosetta` — cada valor con
`displayName` y cita ISDA 2021/2006/2000 (`ACT/ACT.ICMA`, `ACT/ACT.ISDA`,
`ACT/ACT.ISMA`, `30E/360`, `30/360`, `ACT/365.FIXED`, `1/1`, `CAL/252`...).
QuantLib `ActualActual.Convention{ISMA,Bond,ISDA,Historical,AFB,Euro}`.
Strata `StandardDayCounts` (catálogo completo para cross-check).

**Decisión: ADOPT** (la tabla enum como **data canónica**: id + displayName +
aliases + ref ISDA) **+ REFERENCE** (motores de cálculo, no integrados).

**CUSTOM restante**: mapeo lexema ES/EN → canonical con **anchor de contexto
de day-count obligatorio** para lexemas ambiguos; equivalencias ICMA/ISDA/ISMA.

## F5 — call/put (prec 0.7778 < 0.90)

**Root cause**: `list[date]` demasiado pobre + literal `no.` no normalizado +
absorción de label adyacente.

**Upstreams**: QuantLib `Callability` · CDM (reference) · termsheet-eval
`null_inference`.

**Evidencia**: `callabilityschedule.hpp` — `Callability{Bond::Price,
Type{Call,Put}, Date}` + `CallabilitySchedule` (fechas discretas con precio y
lado de la opción). `null_inference.py` categoriza defaults por siblings
(option fields presentes → holder), útil en la capa de **evaluación**, no de
extracción.

**Decisión: PORT_PATTERN** — estructura canónica
`{option_side: ISSUER_CALL|HOLDER_PUT, dates[], price?, notice?, condition?}`.

**CUSTOM restante**: labels ES (`Opción Emisor/Inversor`, amortización
anticipada, precio de reembolso); `'no.'`→NA; schedules MULTI con precio por
fecha.

## F6 — structured products (cap/participation/strike/put_dates sin TP)

**Root cause**: `barrier` aplana **tres** conceptos contractuales;
vocabulario ES no cubierto; pocos docs dev.

**Upstream**: structured-products-toolkit `AutocallNote`/`products.py`
· edgartools `extract_structured_note_terms`.

**Evidencia**: `AutocallNote{autocall_trigger, coupon_barrier,
protection_barrier, pdi_strike, coupon_per_period, memory}` +
`evaluate_autocall` sobre observation-date levels; payoffs
`capital_protected(participation, cap)`, `reverse_convertible(barrier,
pdi_strike)`. Tres barrier roles distintos que nuestro campo único colapsa.

**Decisión: REFERENCE** (semántica canónica + fixtures/oracles de payoff)
**+ PORT_PATTERN** (key-value con catch-all).

**CUSTOM restante**: vocabulario ES (cancelación automática, barrera de
protección, cupón condicionado, strike, participación, techo); tipado de
barrier roles; holdout G1 dimensionado ≥15–20 positivos/familia.

## F7 — extraction architecture

**Root cause**: FIELD_SPECS universal monolítico; sin detección de familia ni
verificación sistemática → errores de contexto recurrentes.

**Upstreams**: vc-statement-parser · contract-rag ·
sovereign-prospectus-corpus · termsheet-extraction-eval.

**Decisión: PORT_PATTERN compuesto** — arquitectura G1:

```text
probe (text_coverage / anchors)
  → classify document_role (signal cascade + REQUIRED data anchors, UNKNOWN ok)
  → family extractor determinista (specs por document_role, no universales)
  → canonical typed model (con barrier roles, callability schedule, day-count enum)
  → verbatim evidence verify (exact_quote in source_text)
  → invariant checks (consistencia cruzada de términos)
```

Eval: taxonomy omission/invention + null inference (termsheet-eval).

**CUSTOM restante**: familias CNMV + specs ES/EN + invariantes contractuales
+ integración con provenance field-level existente.

## F8 — fixed-income-doc-intelligence

Sin LICENSE file (badge MIT ≠ licencia) y el repo **no contiene** el pipeline
anunciado (~312 LOC de scripts sueltos). **REFERENCE** — idea de hybrid
matching (fuzzy+Jaccard+embeddings) como concepto no protegible, nada más.
