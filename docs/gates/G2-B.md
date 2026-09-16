# G2-B — SEMANTIC FIELD RECOGNITION PROBE

**Estado: OPEN (preregistrado)** — experimento único y estrecho. No es una
evaluación de producto ni resucita `GENERAL_EXTRACTION`. Abre tras
`g2-a-final-fail` (`8ad3e2d`, tag `g2-a-final-fail`).

## 0. Motivación

G2-A demostró que el backend documental no es el cuello de botella. El dato
clave sobre DEVELOPMENT cold-issuer:

```text
instancias PRESENT críticas          44
anchor canónico en posición label    24/44 (55%)
anchor semánticamente equivalente    39/44 (89%)
```

Interpretación: en ~89% de los casos la información está localizada, pero el
vocabulario exacto de FIELD_SPECS no reconoce que el texto desempeña ese
papel (e.g. Caixabank `Interés Nominal Anual` → `coupon_rate`).

Hipótesis residual no probada por G2-A:

> Dado únicamente un label/encabezado desconocido, su pequeño contexto
> estructural y opcionalmente el tipo del valor asociado, ¿podemos mapearlo
> a un concepto financiero canónico en un emisor/familia no vistos, sin
> reglas específicas de emisor?

La probe resuelve SOLO `arbitrary label → canonical field`. No extrae el
valor, no produce claims, no toca el verificador.

## 1. Congelaciones heredadas

- `STOP_GENERAL_EXTRACTION` es definitivo para la línea backend/estructura.
- No se prueban más backends, no se optimiza Docling, no se añade vocabulario
  CNMV por emisor.
- Corpus: **solo G1 consumido → DEVELOPMENT** (97 extraction docs). Ningún
  documento nuevo. Holdout G2 sigue sin existir.
- Nada entra en `src/` ni `requirements-lock.txt`. Trabajo en `.work/g2b/`.

## 2. Ontología objetivo

Sin clases nuevas: los 28 campos de `FIELD_SPECS` congelado, agrupados
informativamente:

```text
InstrumentIdentity   isin currency denomination issue_date maturity issued_amount
CouponTerms          coupon_type coupon_rate benchmark spread payment_frequency
                     day_count fixing_rules reset_dates
ExerciseTerms        call_dates put_dates
StructuredPayoff     underlying barrier autocall observation_dates strike
                     participation cap redemption_formula
LegalTerms           ranking subordination business_day_convention settlement_type
```

Referencias CDM/QuantLib/Strata pueden aportar sinónimos genéricos; el
esquema canónico sigue siendo el propio.

## 3. Dataset

Construcción: para cada doc y cada campo con truth `PRESENT`/`MULTI`, se
localiza el valor gold en la IR (bbox de evidencia del predictor cuando es
EXACT, o surface-form del valor gold) y se resuelve el elemento label por
estructura determinista:

```text
TABLE_CELL  -> celda label de la misma fila / header de columna
TEXT        -> prefijo del bloque antes del valor (label: valor)
NEXT_TO     -> bloque predecesor en reading order terminado en ':'
```

Instancias sin label resoluble se contabilizan como `unresolved` y NO entran
en el dataset (no se inventa gold). Clase adicional `UNKNOWN`: bloques en
posición label no asociados a ningún campo de la ontología.

Split (por documento, sin solape de `document_family_key` ni `issuer_key`):

```text
TRAIN+DEV   docs cold_issuer=false   (fitting de aliases/umbrales)
TEST        docs cold_issuer=true    (nunca inspeccionado para diseño)
```

Regla anti-template: el vocabulario de challengers/baselines solo puede
proceder de (a) nombres canónicos genéricos, (b) aliases de FIELD_SPECS
congelado, (c) labels resueltos en TRAIN. Está prohibido codificar variantes
observadas en TEST.

## 4. Input permitido por ejemplo

```text
label_text
heading_path
neighboring_labels
table_position (row/col, is_table)
value_shape (PERCENTAGE | DATE | MONEY | ISIN | ENUM | TEXT | ...)
```

Prohibido: `issuer`, `programme id`, `document_family_key`, coordenadas de
layout conocidas.

## 5. Sistema y salidas

```text
CANONICAL_FIELD   (confidente)
REVIEW
UNKNOWN
```

Nunca se fuerza una clase.

## 6. Comparadores

```text
BASELINE 0   aliases exactos = FIELD_SPECS label-position congelado (==55% cold)
BASELINE 1   similitud léxica normalizada (tokens, acentos, stopwords)
CHALLENGER 1 Valentine (COMA / Cupid / Similarity Flooding / instance-based)
CHALLENGER 2 sentence embeddings multilingües (cosine + umbral calibrado en DEV)
REFERENCE    Sherlock / Sato / Doduo — solo referencia de arquitectura,
             no se entrenan ni se adoptan
```

## 7. Métricas y gates

```text
top1 accuracy (sobre confident)
macro precision / macro recall
REVIEW rate
wrong_confident_mappings      <- hard gate
cold-issuer accuracy/recall
```

Gates preregistrados (sobre TEST cold-issuer):

```text
GATE-SAFETY   wrong_confident = 0            (hard)
GATE-VALUE    recall de reconocimiento >= 80% de instancias resueltas
              (vs ~55% baseline de aliases exactos)
```

`GATE-SAFETY` no negociable: un mapping confundido-confidente es el precursor
directo de los `invented` de G1. `GATE-VALUE` es la señal de que la hipótesis
cambia materialmente el problema; si no se alcanza con `wrong_confident=0`,
la vía no aporta.

## 8. Límite del experimento

```text
G2-B PASS  -> UN test integrado final sobre DEVELOPMENT
              (recognized field + structural relation + typed verifier
              -> supported claim) -> decidir si se justifica hipótesis G3
G2-B FAIL  -> END automated contractual extraction research
```

No hay G2-B.1/B.2/B.3. Los 19 `STILL_FALSE_SUPPORTED` de G2-A son deuda
independiente que esta probe no salda.

## 9. Artefactos

```text
docs/gates/G2-B.md                        (este contrato + veredicto)
g2/research/g2b-label-dataset.json        (dataset + splits + provenance)
g2/research/g2b-environments.json
g2/research/problem-reuse-log.json        (append)
g2/results/g2b-baselines.json
g2/results/g2b-challengers.json
g2/results/g2b-verdict.json
```
