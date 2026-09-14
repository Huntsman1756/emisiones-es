# Linker determinista — registro de reglas (G0-C)

El linker es un **adjudicador**: dado un `source_record` y un candidato,
decide `EXACT_LINK | NO_LINK | AMBIGUOUS` con evidencia explícita
(`rule_id`, `rule_version`, `positive_evidence`, `negative_evidence`).

Código: `src/emissions_es/linking/rules.py` · Orquestador: `linker.py`

## Prioridad de señales (confirmada por el scout)

1. Referencia documental explícita en la fila (enlace NUMFOL)
2. Relación por identificador CNMV exacto (sufijo de versión `.k`/`-k`)
3. ISIN exacto
4. Emisor + programa + evidencia temporal (sucesión **no declarada**
   → no promueve; ver § reglas)
5. Compatibilidad de rol documental

## Reglas registradas

| rule_id | v | entrada | salida |
|---|---|---|---|
| `CNMV_CCFF_EXPLICIT_NUMFOL` | 1.1 | CCFF + candidato folleto | EXACT si el `NUMFOL` **observado en la fila** coincide; NO_LINK si difiere; AMBIGUOUS si la fila no expone NUMFOL o el candidato no expone registro. Si el candidato declara `version`: `supplement.k`/`modification.k` posterior a la fecha de la CCFF → NO_LINK; anterior → AMBIGUOUS (no se puede resolver la versión vigente desde la fila); candidato `base` con suplementos ya registrados a esa fecha → AMBIGUOUS |
| `CNMV_SUPPLEMENT_SUFFIX` | 1.0 | folleto rol SUPLEMENTO | EXACT `SUPPLEMENTS` al registro base X (fila `X.k`) |
| `CNMV_MODIFICATION_DASH` | 1.0 | folleto rol MODIFICACIÓN | EXACT `CORRECTS` al registro X (fila `X-k`) |
| `CNMV_ADMISSION_ISIN` | 1.1 | admisión + candidato security | EXACT `ADMISSION_OF` por ISIN exacto; NO_LINK si difiere; sin ISIN → AMBIGUOUS. Un `record_key` de candidato ajeno a la fila → AMBIGUOUS: el ISIN identifica el instrumento, no el documento; si varias admisiones comparten el ISIN, la fila no desempata |
| `CNMV_SERIE_NO_DOC` | 1.1 | fila SERIE de FTA | `none` → NO_LINK; folleto de otro registro → NO_LINK; folleto del mismo registro sin doc propio en la fila → AMBIGUOUS (el base del fondo no es documento de la serie); doc propio enlazado → EXACT `DEFINES_TERMS_FOR` |
| `CNMV_PROGRAMME_SUCCESSION` | 1.1 | folleto programa + candidato folleto | La fila CNMV **no expone campo de sucesión**: mismo emisor+rol con registro distinto → AMBIGUOUS (la precedencia temporal no prueba REPLACES); emisor distinto → NO_LINK; candidato no observable → AMBIGUOUS |
| `PSE_INSTRUMENT_DOC` | 1.0 | Portfolio doc + candidato security | EXACT `DEFINES_TERMS_FOR` por ISIN de ficha |
| `NO_EVIDENCE_FALLBACK` | 1.0 | cualquier par | AMBIGUOUS (sin candidato: NO_LINK). Nunca promueve por plausibilidad |

## Lo que el linker NO hace

- No enlaza por prefijo de registro (`CCFF_11400_0xx` no implica enlace:
  es un contador de presentaciones sobre el mismo programa).
- No resuelve empates: señales positivas+negativas → `AMBIGUOUS`.
- No usa fuzzy score ni embeddings.

## Invariante

> **La temporalidad registral de CNMV no es un sustituto de una relación
> documental explícita.**

Un registro posterior del mismo emisor y rol no `REPLACES` al anterior:
la fila no expone campo de sucesión. Un suplemento registrado antes que
una CCFF no es automáticamente el documento vigente que definió sus
términos: la fila no dice qué versión aplicó. En ambos casos la única
salida honesta es `AMBIGUOUS`. Caso canónico: `CCFF_11286_014`
(presentada 10/07/2024, con suplementos 11286.1 y .4 ya registrados).

## Scout metrics (56 casos)

`g0/results/linkage-scout-results.json`: accuracy 56/56, 0 FP, 0 FN.
Métrica de desarrollo, no veredicto; los thresholds del holdout no se
tocan. El scout contiene 0 golds `AMBIGUOUS`: su 56/56 **no** valida la
abstención.

## Ambiguity-dev (18 casos, development)

`g0/linkage-ambiguity-dev/cases.json` + `g0/results/linkage-ambiguity-dev-results.json`:
14 golds `AMBIGUOUS` reales (sucesión no verificada, CCFF vs suplementos,
serie vs base, ISIN insuficiente, admisiones hermanas), 3 `NO_LINK`,
1 `EXACT_LINK`. Resultado: 18/18, `forced_ambiguous=0`. Objetivo del
conjunto: 0 enlaces forzados sobre ambigüedad real, no recall.
