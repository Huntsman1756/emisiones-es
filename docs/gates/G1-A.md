# G1-A — SAMPLE ACQUISITION (FROZEN)

Estado: **FROZEN**. Congelado el 2026-09-17 antes de cualquier implementación G1-B.
G1-B no ha comenzado. Ningún extractor, linker ni regla de producción fue modificado.

Cadena de preregistro:

```text
G1 preregistration  4cd3e69
G1 AMEND-1          fd66086   (taxonomía + suficiencia de evidencia)
G1-A0 OSS audit     02a1504
G1 AMEND-2          417917d   (canonical semantics + upstream reuse)
G1-A freeze         este commit
```

## 1. Fuentes y cobertura de adquisición

Nueva adquisición CNMV (todas GET paginadas; el endpoint real de listado
quedó identificado a través del paginador de `busqueda.aspx?id=35`):

| Superficie | Endpoint | Cobertura | Filas |
|---|---|---|---|
| CNMV_CCFF | `condiciones-finales.aspx?fechaDesde&fechaHasta&page` | 2023–2026, todas las páginas | 289 (140 nuevas vs G0) |
| CNMV_FOLLETOS_EMISION | `folletosemisionopv.aspx?fechaDesde&fechaHasta&page` | 2021–2026, todas las páginas | 878 (394 registros únicos nuevos) |
| CNMV_ADMISSION | `folletosadmision.aspx?fechaDesde&fechaHasta&page` | 2024–2026, todas las páginas | 194 (148 nuevos) |
| CNMV_FOLLETO_DETAIL | `folletosemisionopv.aspx?NUMFOL=` | 29 programas referenciados por el pool CCFF nuevo | 46 docs de familia |
| CNMV document service | `webservices/verdocumento/ver?e=` | PDFs | 256/256 OK |

Hallazgo de cobertura: **G0 solo capturó la primera página (~15 filas) por año**
del listado CCFF (152 de 289 reales). La superficie CCFF no indexa años ≤2021
(consultas 2021–2022 devuelven cero filas).

## 2. Universo

`g1/manifests/universe.json` — sha256 `a7d65b5a…`

```text
n_records = 728 (registros únicos; filas multi-ISIN fusionadas por clave)

por acquisition_surface:
    CNMV_FOLLETOS_EMISION  394
    CNMV_ADMISSION         148
    CNMV_CCFF              140
    CNMV_FOLLETO_DETAIL     46

por document_role:
    BASE_PROSPECTUS  344   ISSUE_DOC   135   FINAL_TERMS  140
    SUPPLEMENT        89   CORRECTION    7   SECURITIES_NOTE 13

por instrument_class:
    DEBT 384   OTHER_OR_UNCLEAR 209   EQUITY 135
```

Nota: los recuentos por superficie/rol exactos están en el manifest
(`by_surface`, `by_role`, `by_class`). Cada registro lleva
`acquisition_surface`, `document_role`, `scope_role`, `instrument_class`,
`instrument_subtype`, claves fuente, `document_url`, `document_sha256`,
`local_evidence`, `normalized_row_sha256`, `g0_clean`.

## 3. Deduplicación vs G0 — `duplicates vs G0 = 0`

Tres niveles verificados:

```text
record keys: 728/728 nuevas (CCFF_*, FOL_*, ADM_* no presentes en manifests G0)
doc URLs:    0 solapamientos con .work/pdf_fetches.json (G0)
doc sha256:  3 documentos detectados como duplicados de G0 y excluidos:
             FAM_11327_11327.1  (== G0 X22)
             FAM_11400_11400    (== G0 Y06)
             FOL_11424.1        (flagged g0_doc_duplicate, excluido de holdouts)
```

## 4. Manifests congelados

| Manifest | n | sha256 (prefijo) |
|---|---|---|
| universe | 728 registros | a7d65b5a |
| development | pool nuevo no seleccionado + 300+30 casos G0 | e59e4a20 |
| extraction-holdout | 97 docs | 0442b398 |
| linkage-holdout | 124 casos | f15981fc |
| lifecycle-holdout | 49 casos | cc2b8f3c |
| fetch-index | 256 fetches | 032daaeb |
| freeze | — | a4beaf28 |

Semilla de muestreo: `20260917` (independiente de la semilla G0 `20260914`).

## 5. Extraction holdout (n=97, scope INSTRUMENT_DEFINING)

Estratos (por características fuente `Tipo de Valor` / denominación,
jamás por salida del extractor):

```text
STRUCTURED     41   (CCFF bonos/oblig. estructurados)
PLAIN          23   (20 CCFF simples + 3 ADM bonos)
COVERED        16   (10 CCFF cédulas + 6 ADM cédulas)
SUBORDINATED    4
CONVERTIBLE     4   (ADM)
PROGRAMME       8   (base prospectus de programa renta fija)
PAGARE_LT       1
COVERED_INTL    1
```

Document roles: `FINAL_TERMS` 76, `SECURITIES_NOTE` 13, `BASE_PROSPECTUS` 8.

Expected support proxies (léxico documentado en `lexical_ccff.json`;
no es gold ni salida del extractor):

```text
coupon_rate_family  p_fixed_rate=24 + p_euribor_rate=14 + cupones
                    estructurados (41 docs)   -> esperado >=20
day_count           p_basis=41                -> esperado >=20
call_put            p_callissuer=23, p_put=46 -> esperado >=20
reset_fixing        p_euribor_rate=14         -> esperado ~14 (DESCRIPTIVE_ONLY probable)
structured terms    STRUCTURED=41, p_barrier=38, p_memory=16 -> GATE_ELIGIBLE esperado
subordinated        4 docs                    -> INSUFFICIENT_EVIDENCE probable
```

Los conteos gold reales se determinan en anotación; los proxies solo
justifican la suficiencia esperada del estrato.

## 6. Linkage holdout (n=124)

```text
L1_explicit_family              40  CCFF -> base NUMFOL explícito   LINK
L2_supplement_to_base           18  FAM .k -> base                  LINK (SUPPLEMENTS)
L3_same_programme_role          10  mismo NUMFOL, roles distintos   LINK (BELONGS_TO_SAME_PROGRAMME)
L4_same_issuer_diff_programme   15  mismo emisor, programas dist.   NO_LINK
L5_missing_family               16  FOL .k sin base adquirida       AMBIGUOUS
L6_hard_negative                15  emisores distintos              NO_LINK
L7_succession_candidate         10  mismo emisor, programas         AMBIGUOUS
                                    sucesivos sin relación declarada
```

Truth labels: `LINK` / `NO_LINK` / `AMBIGUOUS`. Salidas operacionales del
sistema G1: `AUTO_LINKED` / `REVIEW_REQUIRED` / `NO_LINK`. Safety:
`false_positive AUTO_LINKED = 0`, `forced ambiguous = 0`.

## 7. Lifecycle holdout (n=49)

```text
SUPPLEMENTS   43   (18 docs de familia detail-page + 25 filas FOL .k)
MODIFIES       7   (filas FOL -k; la CNMV lista la modificación pero no
                   publica PDF separado — evidencia = fila + página de
                   detalle guardada en .work/g1a/detail_*.html)
CORRECTS       0   sin material observable en las superficies adquiridas
REPLACES       0   idem
```

## 8. Development corpus

- 300 casos linkage + 30 casos extraction de G0 (G0 congelado bajo tag
  `g0-final-fail`; elegibles como development).
- 565 registros nuevos del universo no seleccionados en ningún holdout
  (lista en `g1/manifests/development.json`).

## 9. Limitaciones de fuente / licencias

- PDFs CNMV: licencia no redistribuible → `g1/snapshots/*.pdf` gitignored;
  la evidencia comprometida es `document_url` + `document_sha256` +
  `retrieved_at` en `fetch-index.json`.
- `ADM_143062` (convertible): la CNMV no publica documento → excluido del
  holdout de extracción.
- Filas `MODIFICACIÓN` (sufijo `-k`): sin PDF propio; la evidencia es la
  fila de listado + snapshot HTML de la página de detalle.
- Superficie CCFF no indexa ≤2021.
- `folletosadmision` 2021–2026 en consulta única devuelve 1278 páginas;
  se adquirió por año (2024–2026).

## 10. Desviaciones del preregistro

1. El listado ADM se adquirió 2024–2026 (no 2021–2026 completo) por
   volumen; suficiente para el estrato securities-note (13 docs deuda).
2. `REDEPOSIT` / `CORRECTS` / `REPLACES` sin material observable → el
   lifecycle holdout cubre `SUPPLEMENTS` + `MODIFIES` solamente.
3. Extraction holdout n=97 (objetivo ≥60) — crecido para maximizar
   soporte de familias críticas, como permite el preregistro.
4. Ningún documento se seleccionó por resultado del extractor:
   `selection dependence on current extractor = 0` (los proxies léxicos
   son patrones documentados ejecutados sobre texto fuente, no sobre la
   salida del extractor).
5. El listado FOL contiene filas multi-ISIN por registro; el universo
   fusiona por `source_record_key` (955 filas → 728 registros) agregando
   `isin_all`.

## 11. Freeze

`g1/manifests/freeze.json` — sha256 `a4beaf28…`
Incluye: hashes de todos los manifests, seed, thresholds (AMEND-1),
annotation contract (`docs/extraction-contract.md` + `docs/gates/G1.md`),
canonical schema version (AMEND-2 `417917d`).

**Stop**: G1-B implementation no iniciada.
