# Linker determinista — registro de reglas (G0-C)

El linker es un **adjudicador**: dado un `source_record` y un candidato,
decide `EXACT_LINK | NO_LINK | AMBIGUOUS` con evidencia explícita
(`rule_id`, `rule_version`, `positive_evidence`, `negative_evidence`).

Código: `src/emissions_es/linking/rules.py` · Orquestador: `linker.py`

## Prioridad de señales (confirmada por el scout)

1. Referencia documental explícita en la fila (enlace NUMFOL)
2. Relación por identificador CNMV exacto (sufijo de versión `.k`/`-k`)
3. ISIN exacto
4. Emisor + programa + evidencia temporal (sucesión)
5. Compatibilidad de rol documental

## Reglas registradas

| rule_id | v | entrada | salida |
|---|---|---|---|
| `CNMV_CCFF_EXPLICIT_NUMFOL` | 1.0 | CCFF + candidato folleto | EXACT si el `NUMFOL` **observado en la fila** coincide; NO_LINK si difiere (evidencia negativa); AMBIGUOUS si la fila no expone NUMFOL |
| `CNMV_SUPPLEMENT_SUFFIX` | 1.0 | folleto rol SUPLEMENTO | EXACT `SUPPLEMENTS` al registro base X (fila `X.k`) |
| `CNMV_MODIFICATION_DASH` | 1.0 | folleto rol MODIFICACIÓN | EXACT `CORRECTS` al registro X (fila `X-k`) |
| `CNMV_ADMISSION_ISIN` | 1.0 | admisión + candidato security | EXACT `ADMISSION_OF` por ISIN exacto; NO_LINK si difiere |
| `CNMV_SERIE_NO_DOC` | 1.0 | fila SERIE de FTA sin doc propio | NO_LINK: no existe doc-doc observable |
| `CNMV_PROGRAMME_SUCCESSION` | 1.0 | folleto programa + candidato folleto | EXACT `REPLACES` si mismo emisor+rol y registro distinto verificado en KB; NO_LINK si emisor difiere; AMBIGUOUS si no verificable |
| `PSE_INSTRUMENT_DOC` | 1.0 | Portfolio doc + candidato security | EXACT `DEFINES_TERMS_FOR` por ISIN de ficha |
| `NO_EVIDENCE_FALLBACK` | 1.0 | cualquier par | AMBIGUOUS (sin candidato: NO_LINK). Nunca promueve por plausibilidad |

## Lo que el linker NO hace

- No enlaza por prefijo de registro (`CCFF_11400_0xx` no implica enlace:
  es un contador de presentaciones sobre el mismo programa).
- No resuelve empates: señales positivas+negativas → `AMBIGUOUS`.
- No usa fuzzy score ni embeddings.

## Scout metrics (56 casos)

`g0/results/linkage-scout-results.json`: accuracy 56/56, 0 FP, 0 FN.
Métrica de desarrollo, no veredicto; los thresholds del holdout no se
tocan.
