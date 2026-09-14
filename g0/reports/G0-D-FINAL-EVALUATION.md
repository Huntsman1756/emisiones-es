G0 FINAL VERDICT:
FAIL

# G0-D — One-Shot Holdout Evaluation

Apertura única de los holdouts congelados. Sin parches, sin nuevas reglas, sin
extractor v1.2, sin reruns post-reparación. Evaluación válida: verdict FAIL por
incumplimiento de hard gates preregistrados en linkage, extraction y novelty.

## Integrity record

```text
frozen code commit      5426194  (HEAD a3179b9, code-freeze artifact)
code-freeze.json sha    58bf9d09b30dc58337fab35356c4ed5e77256e15e5992a1b928ced99eba44938
environment-lock sha    cb1884fcff36172f466af7652e686fb2027b878b7f8c62af3f49b2f4057c61cc
requirements-lock sha   ba2f63cb78eadb9b26633fb91d62626b3a8f337666e416d982631b1f7a9f4e4d

linkage-holdout sha     a36d37a32845b58f76b2bb75838f38653cb4728219f8bf84244c8e8250996b3f
extraction-holdout sha  f44ce4d0c82fcae34ce493febe234cc85d7b0165e501a05878f2e5ffd1d23f1c
  (before == after; los 30 PDFs verificados byte-a-byte pre y post evaluación)

linkage predictions     4345691d32f671129d9288b727bef0dd9be8051b7902e1ae3756dd2f880b88c1
extraction predictions  2967a6f7b657df76c27f7dbfb8eb8f29cd28e861af5860f1746bbbf48d422c17
extraction truth sha    378567788c6ac17e36f72d1d255030ee5778f22eabd7db8a79ce7178fc541694
                        (v1.1 — incluye 2 erratas documentadas, ver desviaciones)

linkage score           0384f02c6d125050d7a7bc5b9a9b1e108e4afccaa998d9f3deaf3f1cea84c7fb
extraction score        c145201ba0b5062ddccef0a09da0a2dfb362a56dfd6602ce0e4e080689780651
novelty score           392ad9e95520d4837831209f2b167f7034c0e55e8651f47aaa370e82bed01593
provenance score        2d6b5707668c70a4bc64a8b7481c2e916013e9341830c4f71e9f2a442edfdf10
performance             39a07c103f489ce743fec5ddc70a956b8177c994bc61e7b66f0b554cb9ddadbf
```

Pre-flight ejecutado antes de abrir holdouts: 46/46 tests PASS, linkage scout
56/56, ambiguity-dev 18/18, forced_ambiguous 0, freeze guard PASS, código ==
code-freeze.

Pipeline real (terminología corregida): Docling `DocumentConverter()` defaults —
`do_ocr=True` (RapidOCR/torch), `do_table_structure=True` (TableFormer ACCURATE,
cell_matching). Los extractores y el linker son deterministas sobre la
representación de Docling; la capa de parsing incluye modelos ML. No es
"fully deterministic PDF parsing". Sin extracción factual con LLM y sin
escalado gmft/Camelot.

## OFFICIAL G0 RESULT

```text
Gate                        Result        Threshold      PASS/FAIL
-------------------------------------------------------------------
Linkage accuracy            88.3%         >= 98%         FAIL
Linkage precision           100%          >= 99%         PASS
Linkage recall              88.8%         >= 95%         FAIL
False positive links        0             0              PASS
Forced ambiguous            0             0              PASS
Extraction: coupon/rate     prec 93.3%    >= 95%         FAIL
Extraction: day_count       prec 93.75%   >= 95%         FAIL
Extraction: maturity        prec 100%     >= 99%         PASS
Extraction: call/put        prec 77.8%    >= 90%         FAIL
Extraction: reset/fixing    prec 92.3%    >= 90%         PASS
Extraction: observation     prec 100%     >= 90%         PASS
Extraction: barrier/strike/
  redemption                prec 100%     >= 90%         PASS
Provenance                  258/258       100% backed    PASS
Novelty (OSS_DELTA)         21/30 = 70%   >= 24/30       FAIL
Freeze integrity            unchanged     unchanged      PASS
```

**Verdict: FAIL** — 3 hard gates de linkage/extraction/novelty por debajo de
threshold con evaluación válida. No "near pass": accuracy linkage 88.3 vs 98,
novelty 70 vs 80, call/put precision 77.8 vs 90.

## Linkage holdout (n=300)

```text
gold:       EXACT_LINK 224 · NO_LINK 69 · AMBIGUOUS 7
predicted:  EXACT_LINK 199 · NO_LINK 63 · AMBIGUOUS 38

exact-target accuracy  265/300 = 88.33%
tp=199 fp=0 fn=25   precision 1.0 · recall 88.84%
ambiguous: gold 7 · correctamente abstenidos 5 · forced 0
```

Fallos por estrato (35 total):

```text
S4_programme_succession        25/25   gold=EXACT_LINK, pred=AMBIGUOUS
S7_same_programme_diff_role     8/8    gold=NO_LINK,    pred=AMBIGUOUS
S9_no_link_insufficient         2/24   gold=AMBIGUOUS,  pred=NO_LINK
```

Taxonomía diagnóstica: `MISSING_EXPLICIT_REFERENCE` 25 · `RULE_DEFECT` 10.
Todos los demás estratos 100% (S1 98/98, S2 50/50, S3 10/10, S5 35/35,
S6 15/15, S8 15/15, S10 15/15, S11 5/5).

Lectura: el linker nunca forzó un enlace — precisión 1.0, FP 0, forced 0. El
fallo es de cobertura: la fila CNMV no declara explícitamente la sucesión de
programa (S4) ni la distinción de rol (S7), y las reglas congeladas abstienen
correctamente ante insuficiencia pero el gold esperaba resolución por
sucesión temporal / rol documental. Es un defecto de recall de las reglas,
no de integridad del enlace.

## Extraction holdout (n=30)

Totales del scoring contract congelado (`deep_dev_metrics.classify`):

```text
TP 254 · FN 147 · TN 242 · CORRECT_NA 26
TP_RAW 8 · FP_RAW 9 · SPURIOUS_NA 6 · FN_NA 2 · FP 4
```

Per-field (ver `g0-d-extraction-score.json` para detalle por caso):

```text
field                     TP RAW FP sNA FN cNA  TN  prec    rec
isin                       19  0  0  0  5   0   4  1.000  0.792
currency                   16  0  0  0  7   0   0  1.000  0.696
issue_date                 19  0  0  0  3   0   1  1.000  0.864
maturity                   15  0  0  0  8   0   5  1.000  0.652
denomination               14  0  0  0  8   0   0  1.000  0.636
issued_amount               5  0  0  0 17   0   0  1.000  0.227
coupon_type                19  0  2  0  3   0   4  0.905  0.864
coupon_rate                 9  0  0  0 13   0   2  1.000  0.409
benchmark                   9  0  0  0  3   0  16  1.000  0.750
spread                      6  0  0  0  9   0  13  1.000  0.400
payment_frequency          10  2  0  0 11   0   5  1.000  0.522
day_count                  15  0  1  0  4   0   4  0.938  0.789
call_dates                  5  2  0  0  8   6   5  0.778  0.467
put_dates                   0  0  0  0  7   8   8     —    0.000
reset_dates                 4  0  0  0  7   0  12  1.000  0.364
fixing_rules                8  0  0  1  4   0  10  0.889  0.667
business_day_convention    18  0  0  0  4   0   1  1.000  0.818
ranking                     8  0  0  0  2   0  12  0.889  0.800
subordination               1  2  0  0  2   0  13  0.375  0.600
redemption_formula         19  0  0  0  4   0   5  1.000  0.826
underlying                  8  0  1  3  4   0  12  0.667  0.667
strike                      0  0  0  0  2   0  21     —    0.000
barrier                     3  1  0  0  4   0  20  1.000  0.500
participation               0  0  0  0  3   0  20     —    0.000
cap                         0  0  0  1  2   7  12  0.000  0.000
autocall                    2  0  0  1  1   5  14  0.667  0.667
observation_dates           4  1  0  0  0   0  18  1.000  1.000
settlement_type            18  0  0  0  4   0   5  1.000  0.818
```

Patrones de error (diagnóstico, no altera métricas):

- **Absorción de label adyacente / NA espurio**: `Not Applicable` de un label
  vecino atribuido al campo (X17 settlement_type, X20 autocall, X02/X07/X09/X11
  underlying, X19 cap/fixing_rules). Clase dominante de FN_NA/SPURIOUS_NA.
- **Conflación ranking/subordination**: raw `Senior ... Notes` emitido bajo
  `subordination` con valor None (X04, X05, X07, X09, X28) → FP_RAW.
- **Literal `no` no normalizado**: `para el Emisor: no.` en CCFF no reconocido
  como NA (X10, X13 call_dates → FP_RAW).
- **Promoción de fragmento**: X18 coupon_type (texto de ajuste de maturity),
  X30 underlying (`en que se basa el tipo`), X19 day_count (`1/1`).
- **Ruido tabular en documento no-instrumento**: X26 (folleto DRU) generó
  CONFLICT de coupon_type con porcentajes de estados financieros — contenido
  por CONFLICT, no adjudicado silenciosamente.
- **Candidato extra en multi-valor**: X19 isin CONFLICT mezcla el ISIN de la
  nota (ES0305067L91) con el ISIN de la acción subyacente (US69608A1088) —
  `extra incorrect candidate` bajo §10.
- **Formato no cubierto**: X28 (securities note de admisión) solo extrajo 4
  campos — el template label:value del CCFF/final-terms no aplica; X27
  (folleto ABS multi-tramo) no capturó ISINs por tramo.

## Provenance

```text
accepted factual values: 258 · evidence-backed: 258 · pct 1.0
invented/unsupported values: 0 · VALUE_CORRECT_PROVENANCE_BAD: 0
gate: PASS
```

Todo valor emitido lleva `source`, `snapshot_sha256`, `page`, `excerpt` (raw
lexeme) e `extractor` id/versión por item de evidencia.

## Novelty / OSS_DELTA (oficial)

```text
has_material_document_only_delta: 21/30 = 70.0%  ·  threshold >= 24/30  →  FAIL
```

Por estrato:

```text
plain_vanilla 5/5 · coupon_variant 4/4 · covered_bond 4/4
subordinated 2/2  · structured 5/5      · securitisation 1/1
supplement 0/3 · correction 0/2 · registration 0/1
admission_debt 0/1 · admission_equity 0/1 · commercial_paper 0/1
```

Los 9 documentos sin delta son todos documentos no-definitorios de instrumento
(supplements, corrections, registration, admissions, CP programme) salvo
`admission_debt` (X28, securities note con formato no cubierto por los
extractores). Ningún campo se reclasificó; `document_lineage` no cuenta como
término material por sí solo.

## Performance

Extracción (30 docs, post-conversión): total 7.5s · median 0.0s · p90 0.2s ·
max 3.9s. Conversión Docling full KEEP_FULL domina el coste (X26: 1644s,
788pp; total conversión ≈ 30 docs incl. varios folletos de 200–800pp).
No forma parte del hard gate.

## Desviaciones registradas

Audit trail completo y permanente: `g0/reports/G0-D-AUDIT-TRAIL.md`
(truth v1.0/v1.1 + diff + evidencia; scorer provenance antes/después).


1. **Scorer de provenance (tooling de evaluación, no código congelado)**:
   criterio corregido para aceptar raw lexeme en `evidence[].excerpt` (diseño
   real del contrato) en vez de exigir `raw_lexeme` top-level. Predicciones no
   re-ejecutadas.
2. **Truth errata v1.1** (2 correcciones objetivas verificables en el
   documento, encontradas durante análisis de errores post-scoring; ambas
   documentadas con evidencia y dirección dentro del JSON de truth):
   - X02 `ranking`/`subordination` ABSENT→PRESENT — el doc contiene
     `(i) Status of the Notes: | Senior Non-Preferred Notes` (p.2). El FP
     de ranking era en realidad un TP.
   - X20 `call_dates`/`put_dates` ABSENT→NA — el doc dice `Opción Emisor:
     No Aplicable.` / `Opción Inversor: No Aplicable.`. Dirección conservadora:
     añade 2 FN al grupo call/put.
   Truth re-hasheado (37856778…); un único re-scoring posterior a las erratas.
3. `g0-d-linkage-score.json` materializa el resultado ya sellado de
   `linkage-holdout` con thresholds; no se re-ejecutó inferencia.
4. Docling emitió warnings de bbox negativos en tablas de X26 (clampeados);
   conversión correcta, sin cambio de pipeline.

## Hallazgos inesperados

- El fallo de linkage S4 no es ruido ni trampas temporales: es ausencia real
  de referencia explícita en el registro CNMV. El diseño de abstención hizo
  exactamente lo que debía (0 enlaces forzados) — el gap es de cobertura de
  reglas, no de seguridad.
- Provenance al 100% con 258 valores: el diseño field-level de evidencia se
  sostiene en holdout sin excepciones.
- Los formatos "securities note" y folletos multi-tramo quedan fuera de la
  cobertura estructural de los extractores — un fallo de formato, no de lógica
  de campos.

## Limitaciones

- Truth anotada por un único anotador (yo) desde dumps Docling; erratas
  descubiertas post-seal demuestran que la anotación tiene tasa de error no
  nula en campos tabulares de folletos EN.
- n=30 con estratos heterogéneos: métricas por campo con denominadores
  pequeños (strike n=2, participation n=3, put_dates n=7).
- `NO_DEV_EVIDENCE` (cap, participation, strike) confirmado en holdout: 0 TP —
  los misses cuentan como FN, no exentos.
- La representación de Docling (OCR+TableFormer) es la entrada: errores de
  conversión (columnas, tablas financieras) se propagan a extracción.

---

# POST-HOC PRODUCT INTERPRETATION

(Separado del resultado oficial. No altera el verdict FAIL.)

- El delta documental existe donde el producto lo necesita: **documentos
  definitorios de instrumento = 20/20 con delta (100%)**; issuance-like amplio
  (incl. admission_debt, corrections, securitisation) = 20/23. El FAIL oficial
  viene de incluir supplements/corrections/registration/admissions en el
  denominador preregistrado — documentos que no definen términos. Un gate G1
  con scope "instrument-defining documents" podría ser la reformulación
  honesta, no una exención retrospectiva.
- La asimetría precision 1.0 / recall bajo en linkage sugiere que la
  resolución de sucesión de programa requiere evidencia que el registro CNMV
  no declara explícitamente — posiblemente inferencia temporal legitima
  preregistrable, o adquisición de fuente adicional (BME, folletos).
- Los fallos de extracción son mayoritariamente de recall y de clases
  acotadas (atribución de labels adyacentes, conflación ranking/subordination,
  formatos no-CCFF), no de invención de valores (0 unsupported).
- La inversión en Docling full es viable para 30 docs; para backfill masivo,
  el prescan selectivo tendría que demostrar merge de provenance — decisión
  pospuesta correctamente.
