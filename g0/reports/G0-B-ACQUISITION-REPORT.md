# G0-B — Acquisition & Holdout Freeze — Informe

Fecha de congelado: 2026-09-14 · Repo: `F:\_Proyectos\emisiones-es`

## Veredicto: PASS

Las superficies núcleo de CNMV son adquiribles de forma reproducible por
HTTP directo, las URLs documentales se resuelven para todo el corpus, la
identidad de fila/documento es auditable, el versionado sin overwrite
está demostrado, y los conjuntos scout/holdout quedaron congelados
antes de escribir reglas.

## 1. Qué se adquirió

| Familia | Superficie | Resultado | Filas/Docs |
|---|---|---|---|
| Folletos emisión/OPV | `busqueda?id=19` → GET paginado | ✅ 200 | 468 filas (2021–2026) |
| Folletos admisión | `busqueda?id=20` → GET paginado | ✅ 200 | 65 filas |
| Condiciones finales (CCFF) | `busqueda?id=35` → GET paginado | ✅ 200 | 152 filas (2023–2026) |
| Detalle folleto | `folletosemisionopv.aspx?NUMFOL=` | ✅ 301→200 | agrupa base+supl.+series |
| Servicio documentos | `verdocumento/ver?e=` | ✅ 200 PDF | 41/41 PDFs verificados |
| Infraestructuras | `rectoras/listadosim` | ✅ 200 | lista completa venues |
| Consulta ISIN | `ancv/isin.aspx` | ⛔ 403 | no requerida para corpus |
| Operaciones semanales | `CNMVInforma.aspx` | ⛔ 403 | auxiliar, no núcleo |
| Pasaportes | `busqueda.aspx?id=11` | ⚠️ 400 inicial | fuera del corpus mínimo |
| Portal `internet.cnmv.es` | SPA + suggest API | — | sin API de registro; HTML-first confirmado |
| Portfolio Stock Exchange | fichas + `api.portfolio.exchange/poex/document/{id}` | ✅ limitado | docs requieren `Referer`; sin deuda listada |
| Securitize (DLT) | — | NOT_AVAILABLE | sin emisión pública |

**PDFs resueltos: 41/41** (30 holdout + 11 scout), todos con `sha256`,
`retrieved_at` y `local_evidence` en `g0/snapshots/` (gitignored).

## 2. Identidad CNMV verificada

Probes del brief resueltos sobre datos reales:

- `CCFF_11400_043/044/045` — Santander, programa 11400 (5.000M€
  PROGRAMA RENTA FIJA, reg. 23/12/2025): **mismo registro oficial, 3+
  condiciones finales, ISINs distintos, fechas distintas** → confirma
  que `registro_oficial` no es id de fila.
- `CCFF_11425_001` — ABANCA, 500M, `ES0265936080`, AIAF. Edge case: el
  detalle `NUMFOL=11425` solo muestra el suplemento `11425.1`, no la
  base → conservado como caso `AMBIGUOUS` (S11-001).

Modelo provisional congelado en `docs/acquisition-contract.md` §4:
`source_record_key` / `source_document_key` /
`programme_or_prospectus_reference` / `isin` / `observed_version`.

## 3. Versionado / reobservación

`tools/reobserve.py` clasifica pares de observaciones. Resultados en
`g0/results/reobservation-results.json`:

- 3 pares reales misma ventana (CCFF Santander, folleto 11434,
  listadosim): **UNCHANGED** ×3.
- 1 par real entre capturas (detalle 11434): **UPDATED_METADATA** —
  raw difiere (ViewState/sesión), filas idénticas. Demuestra que el
  envoltorio HTML muta sin que muten las filas.
- Fixtures: UPDATED (fila), DISAPPEARED (404), NEW cubiertos.

## 4. Conjuntos congelados

| Conjunto | n | Manifest | sha256 (16) |
|---|---|---|---|
| Linkage scout | 56 | `linkage-scout.json` | `99239b442bd1b70e` |
| Linkage holdout | 300 | `linkage-holdout.json` | `e0f711bfa1de3c10` |
| Extraction scout | 11 | `extraction-scout.json` | `670ac8382753bce1` |
| Extraction holdout | 30 | `extraction-holdout.json` | `465a70efac101eb0` |

Estratos del holdout de linkage (reglas de muestreo en el manifest):

```text
S1 final_terms→programme     98   EXACT (NUMFOL explícito en fila CCFF)
S2 supplement→prospectus     50   EXACT (registro X.k → X)
S3 correction→document       10   6 EXACT (X-k → X) + 4 NO_LINK cruzados
S4 programme_succession      25   EXACT (mismo emisor, mismo rol, reg. consecutivo)
S5 admission→security        35   EXACT (ISIN explícito)
S6 same_issuer_wrong_prog.   15   NO_LINK
S7 same_programme_diff_role   8   NO_LINK (CCFF ↔ suplemento hermanos)
S8 similar_title_diff_issuer 15   NO_LINK
S9 no_link/insufficient      24   NO_LINK/AMBIGUOUS (series sin doc, sin enlace)
S10 multi_venue              15   admisión multisede / FTA sin admisión
S11 ambiguous_ground_truth    5+  AMBIGUOUS manual (11425, 2026xxxxx, CCFF mismo ISIN)
```

Labels por construcción estructural (`label_source`), no por juicio
manual salvo S11. Ningún extractor ni linker se ha implementado; las
labels del holdout no han influido regla alguna (no existen reglas).

Pools: 437 folletos / 123 CCFF / 57 admisiones en pool holdout tras
excluir los ~40 registros inspeccionados en discovery (scout).

## 5. Portfolio Stock Exchange

- La ficha de instrumento embebe metadatos de documentos
  (`Documento de Emisión`, versiones, cuentas, avisos) con URLs
  `api.portfolio.exchange/poex/document/{id}`.
- Descarga directa: 403 sin headers → **200 application/pdf con
  `Referer: https://portfolio.exchange/`** (verificado, sha256
  registrado; doc 2589 AC Residencial en scout Y11).
- **Casos de deuda encontrados: 0.** Los 31 valores listados son
  SOCIMI/equity; el rulebook soporta bonos pero no hay emisión de deuda
  listada que congelar. Desviación documentada; el mecanismo documental
  queda probado y el estrato de extracción Portfolio se cubre con un
  documento de emisión equity real.

## 6. Securitize / DLT

`DLT_CASE = NOT_AVAILABLE`. Autorizada por CNMV (2025-11-26, Reg. UE
2022/858) pero sin emisión pública documentable localizada. No se forzó
caso artificial. El modelo de venues la conserva como design-case.

## 7. Desviaciones vs preregistro

1. Portfolio: 0 casos de deuda (mercado real es equity-only hoy).
2. DLT: NOT_AVAILABLE (con evidencia).
3. S4 reinterpretado: sucesión anual de programa en lugar de
   "redeposit" literal (no observable como fila; ver gate doc).
4. `consulta_isin`/`CNMVInforma` 403 — auxiliares, no núcleo.
5. Cobertura CCFF corta (desde ~2023); suficiente para 300/30.
6. Sustituciones scout: `ADM_143237→ADM_143231`, `FOL_11424.1→FOL_11425.1`
   (mismo estrato/regla; documentadas).
7. `coupon_variant_candidate` (X06–X09): la superficie no distingue
   fijo/variable; se preregistran como candidatos a cupón variable a
   verificar en extracción — honestidad antes que inferencia.

## 8. Riesgos abiertos para G0-C/D

- Tokens `verdocumento` opacos: la identidad documental depende de
  URL+hash; si el token rota, el historial por URL canónica puede
  romperse (mitigado: nunca sobrescribir, `normalized_row_sha256`).
- Redepósitos/correcciones solo detectables por reobservación
  programada — no hay superficie que los liste como versiones.
- Portfolio deuda: si el mercado sigue sin emisiones, el estrato
  multi-venue de deuda quedará cubierto solo por AIAF/MARF vía CNMV.

**Stop.** No se continúa a implementación de linker/extractores.
