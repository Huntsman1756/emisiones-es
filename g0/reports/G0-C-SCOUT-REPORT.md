# G0-C SCOUT IMPLEMENTATION — Informe

HEAD de partida: `a3e659eaba30146f638a8c0d85426a93d02756b9`
Freeze verificado al inicio y al cierre: **byte-identical** (ver
`docs/gates/G0-C-SCOUT.md` para hashes completos).

> Alcance estricto: `linkage-scout=56` y `extraction-scout=11`.
> Los holdouts (300 / 30) no se abrieron, inspeccionaron ni puntuaron.

## 1. Código custom añadido

| Módulo | Contenido |
|---|---|
| `src/emissions_es/model/` | Modelo canónico mínimo Pydantic: `SourceObservation`, `Document`, `DocumentIdentifier`, `DocumentRelation`, `Issuer`, `Instrument`, `InstrumentIdentifier`, `Programme`, `Venue`, `InstrumentVenue`, `TermObservation`, `EvidencePointer`, `ReconciliationObservation`, `Conflict`, enums de estado |
| `src/emissions_es/linking/rules.py` | Rule registry: 8 reglas explícitas (`rule_id`, `version`, evidencia +/−) |
| `src/emissions_es/linking/linker.py` | Adjudicador determinista source_record×candidate |
| `src/emissions_es/extraction/docview.py` | `NormalizedDocumentView`: adaptador sobre `DoclingDocument` (textos, tablas, prov/page/bbox, lookup geométrico, `evidence_for`) |
| `src/emissions_es/extraction/normalize.py` | Normalizadores deterministas: números ES/EN, fechas ES/EN, %, divisa (incl. CNH), importe, ISIN |
| `src/emissions_es/extraction/extractors.py` | Registry `FIELD_SPECS`/`EXTRACTORS` — 14 campos, anclas bilingües, estrategias label→valor con resolución geométrica y anti-fuga |
| `src/emissions_es/reconciliation/` | `reconcile()` (AGREE/CONFLICT/SOURCE_ONLY/MISSING/NOT_APPLICABLE) + oracle de calendario `expected_schedule`/`check_schedule` (VALID/INVALID/UNVERIFIABLE) |
| `src/emissions_es/provenance/` | `EvidencePointer` re-export + `sha256_file`, `snapshot_pointer` |
| `tools/` | `run_linkage_scout.py`, `run_extraction_scout.py`, `docling_baseline.py` (incremental, cachea DoclingDocument por documento) |
| `tests/` | `test_freeze_guard.py` (integridad de manifests+thresholds), `test_core_g0c.py` (22 tests) |

## 2. Linkage scout (56 casos)

```text
n=56  accuracy=56/56
tp=44  fp=0  fn=0
precision=1.0  recall=1.0
ambiguous_predicted=0  ambiguous_gold=0  forced_ambiguous=0
```

Resultados: `g0/results/linkage-scout-results.json`.
El linker es un adjudicador: cada decisión cita `rule_id`+`version`,
evidencia positiva y negativa. No usa fuzzy score ni labels de holdout.
Reglas documentadas en `docs/linking-rules.md`.

Casos estructurales verificados:

- `CCFF → NUMFOL` explícito por enlace observado en fila.
- `FOL_11424.1` → `SUPPLEMENTS` a `11424`; `FOL_11365-1` → `CORRECTS` a `11365`.
- `ADM_*` → `ADMISSION_OF` por ISIN exacto.
- SERIE sin documento propio → `NO_LINK` (evidencia negativa).
- Mismo emisor, distinto programa → `NO_LINK`.
- `PSE_ACRS` → `DEFINES_TERMS_FOR` por ISIN de ficha Portfolio.
- CCFF cuyo NUMFOL no es observable en fila → `AMBIGUOUS` (no forzado
  por falta de candidato: `NO_LINK`).

## 3. Extraction scout (11 documentos, primera ola)

14 campos: isin, currency, issue_date, maturity, denomination,
issued_amount, coupon_type, coupon_rate, benchmark, spread,
payment_frequency, day_count, call_dates, business_day_convention.

Resultados: `g0/results/extraction-scout-results.json`.

Cobertura (Docling-only, anclas bilingües + resolución geométrica):

- **CCFF ICMA EN** (Y01, Y02, Y03): 10–11/14 campos con evidencia
  reproducible (page+bbox+lexema). Y03 resolvió el label partido
  `Aggregate Nominal`/`Amount:` por geometría → `EUR 500,000,000`
  (coherente con la fila CNMV 11425, no copiado de ella).
- **CCFF ES cédulas** (Y04): identidad/importes correctos; cupón,
  frecuencia y day-count salen `CONFLICT` — el instrumento tiene
  régimen fijo inicial + variable en prórroga. Conservar el conflicto
  es el comportamiento correcto (no se colapsa).
- **CCFF estructurado** (Y05): ISIN/fechas/cupón/día-cálculo extraídos;
  campos de índice de crédito quedan fuera de la primera ola →
  `MISSING` honesto.
- **Folleto base** (Y06): plantillas `[[   ] per cent. Fixed Rate]` →
  `MISSING` (guard anti-placeholder: una plantilla no es un hecho).
- **Suplemento** (Y07): 0 campos de primera ola — honesto; el
  suplemento no redefine términos completos.
- **FTA** (Y08): ISIN → `CONFLICT` con los 4 ISINs de series A1/B/D/F
  (representación honesta de multi-serie).
- **DRU** (Y09): divisa EUR extraída; `coupon_type` → `CONFLICT` con
  las tasas de la tabla de tramos del documento de registro (el DRU no
  es un documento de emisión concreta: cubre el programa completo).
- **Admisión** (Y10): ISIN `ES0162600003` extraído — el documento de
  admisión sí lleva identificador de instrumento.
- **Portfolio** (Y11): ISIN `ES0105746004` extraído del Documento de
  Emisión (equity scout; no es deuda — `PORTFOLIO_DEBT_CURRENTLY_OBSERVED
  = 0` se mantiene).

`spread` → `MISSING` en los 11: ningún scout de primera ola expone
spread explícito (los instrumentos son fijos, reset o CLN sin margen
anclado simple). Ausencia conocida, no fallo silencioso.

Guardas implementadas (problemas reales descubiertos en scout):

- Prefijo numérico ICMA opcional `(i)`, `(xxii)`, `45.`, `b)`.
- `VERB_LEAK`: "is/are/es/son…" tras el ancla no es valor.
- `_placeholder`: `[[ ] ]`, `[●]` sin dígito → no promover.
- ISIN auto-ancla (standalone o `Código ISIN: …` embebido).
- Labels partidos en dos ítems consecutivos + resolución geométrica
  (valor a la derecha de cualquiera de las líneas; subfilas
  Series/Tranche/Total/Nominal).

## 4. Docling baseline (determinista, medido)

`g0/results/docling-baseline.json` — docling 2.126.0.

| doc | páginas | textos | tablas | kv | tiempo |
|---|---|---|---|---|---|
| Y01 CCFF | 9 | 151 | 2 | 0 | 22.5 s |
| Y02 CCFF | 9 | 186 | 1 | 0 | 17.1 s |
| Y03 CCFF | 8 | 102 | 5 | 0 | 9.9 s |
| Y04 CCFF | 7 | 154 | 1 | 0 | 5.6 s |
| Y05 CCFF | 19 | 402 | 12 | 0 | 29.5 s |
| Y06 folleto | 333 | 5244 | 45 | 0 | 263.5 s |
| Y07 suplemento | 4 | 36 | 0 | 0 | 2.6 s |
| Y08 FTA | 254 | 7118 | 81 | 0 | 517.6 s |
| Y09 DRU | 681 | 15484 | 517 | 0 | 1870.8 s |
| Y10 admisión | 59 | 680 | 32 | 0 | 76.2 s |
| Y11 PSE | 35 | 464 | 10 | 0 | 23.6 s |

Peak RSS por documento registrado en el JSON (máx. +883 MB en Y01 por
inicialización del pipeline; Y09 +725 MB).

Observaciones del baseline:

- `key_value_items` = 0 en todos: el layout label→valor llega como
  textos+tablas, no como KV — el adaptador geométrico es necesario.
- TableFormer de Docling emite miles de `Orphan pdf_cell … recovered by
  nearest-row/column fallback`: la extracción tabular de CCFF/FTA es
  *aproximada por heurística de proximidad*, no por rejilla fiable.
- RapidOCR/Torch se inicializa aunque el PDF tenga texto (Y09 muestra
  OCR de páginas escaneadas): coste de RAM/RSS cuantificado por doc.
- Runtime domina en folletos base (263–518 s para 250–333 pp);
  las CCFF (<20 pp) cuestan 5–30 s.

## 5. Reconciliación y oracle

- `reconcile()` implementado y testeado: AGREE/CONFLICT/SOURCE_ONLY/
  MISSING/NOT_APPLICABLE; los CONFLICT conservan todas las fuentes.
- Oracle de calendario: `expected_schedule(freq, issue, maturity)`
  → VALID/INVALID/UNVERIFIABLE. Testeado (anual 10 periodos OK,
  frecuencia ausente → UNVERIFIABLE, maturity<issue → INVALID).
  No se ejecuta contra el holdout; es un chequeo de consistencia,
  no una fuente de verdad.

## 6. Necesidad de ML tabular — cuantificación (no asumida)

- Campos de primera ola resueltos por texto+geometría en CCFF: la
  mayoría sin necesidad de tabla estructurada (los labels viven en
  textos sueltos o tablas simples).
- Fallos tabulares observados: orphan-cell recovery masivo en Y05/Y08
  (Docling aproxima). Ningún campo de primera ola en el scout requirió
  gmft/Camelot: **0 documentos exigieron escalado tabular para los
  campos objetivo**; el coste visible es calidad de tablas complejas
  (schedules de amortización FTA, tablas de series) que pertenecen a
  segunda ola.
- Delta de fallback tabular: **no probado** — no hubo un fallo concreto
  reproducido en primera ola que lo justificara (condición del brief).

## 7. Tests

`python -m pytest tests/` → **22 tests OK**: identificadores,
relaciones, reglas de linker (incl. `CCFF_11400_043/044/045` mismo
registro ≠ mismo registro-de-presentación → no enlaza por prefijo),
evidencia negativa, abstención AMBIGUOUS, normalizadores
número/fecha/%/divisa, preservación de evidencia, estados de
reconciliación, oracle, licensing guard.

## 8. Límites OSS

Dependencias OSS realmente usadas: `docling 2.126.0` (parseo baseline),
`docling-core` (DoclingDocument/JSON), `pydantic 2.13.5` (modelo).
**Ninguna** de `gmft_pymupdf`, `PyMuPDF`, `Marker`, `MinerU`,
`rateslib` entra al core — guard automatizado en
`tests/test_core_g0c.py::test_no_forbidden_deps_in_package` +
`test_no_forbidden_deps_declared`.

## 9. Desviaciones

- `pyproject.toml` declara `requires-python = ">=3.13"` pero el
  entorno de ejecución real es CPython 3.11 (uv). El código no usa
  features 3.13; se deja constancia (cambio de manifiesto fuera del
  alcance de este gate).
- Cobertura CCFF CNMV ≈2023+ (heredado de G0-B): histórico requerirá
  navegación por folletos/relaciones.
- Y05 `payment_frequency` capturó rango de periodo en prosa ("and
  including…") — lexema real preservado, pero la normalización a
  frecuencia canónica queda para segunda ola. Limitación registrada,
  no maquillada.
- Y08 `benchmark` capturó fragmento de prosa del disclosure de tipo
  de referencia (real, con evidencia, pero no el nombre del índice).

## 10. Veredicto G0-C

```text
PASS
```

Justificación: la arquitectura determinista adjudica los 56 enlaces
scout con 0 FP y evidencia auditable por regla; los términos
contractuales de primera ola se extraen con evidencia reproducible
(página+bbox+lexema) sin inventar valores; los conflictos reales se
conservan; no se necesita ML tabular ni dependencia prohibida para la
primera ola; los holdouts permanecen byte-idénticos.

**Detenido aquí.** No se ejecutan los 300 casos de linkage holdout ni
los 30 documentos de extraction holdout; la apertura requiere una fase
separada con código congelado.
