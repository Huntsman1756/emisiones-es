# G1-A1 — Sampling Bias Audit

## Dos holdouts, dos preguntas distintas

```text
extraction holdout (n=97)
    pregunta: ¿puede el sistema extraer términos con precisión/recall?
    diseño:   CHALLENGE SET — deliberadamente enriquecido en structured,
              call/put, barrier, FRN. NO representativo de prevalencia.
    uso válido: precision/recall/coverage, family gates, provenance, safety.
    prohibido: inferir prevalencia poblacional de OSS_DELTA.

novelty holdout (n=100)
    pregunta: ¿qué fracción de documentos INSTRUMENT_DEFINING aporta
              ≥1 término material DOCUMENT_ONLY?  (gate: novelty ≥80%)
    diseño:   simple random sample del universo elegible, seed 20260917.
```

## Novelty holdout — método

```text
población elegible:  scope_role=INSTRUMENT_DEFINING, g0_clean,
                     document_url presente, no en otros holdouts
n elegible:          291
n muestreado:        100 (SRS sin estratificar)
seed:                20260917
weighting required:  no (SRS → estimador directo)
estimador:           novelty_rate = material DOCUMENT_ONLY / elegibles
IC:                  exacto binomial 95%
```

Independencia: las familias de los docs de novelty entran en el conjunto
`holdout_families`; sus hermanos quedan fuera de development (quarantine).
Sin solape con extraction/linkage/lifecycle por construcción.

`has_material_document_only_delta` se determina contra el documento +
novelty-field-map congelado + contrato de disponibilidad FIRDS/ESAP/CNMV —
**no** contra la salida del extractor G1. NOVELTY=TRUE con FN del extractor
sigue siendo novelty.

## Lexical proxies

Los flags `p_*` (callissuer, put, basis, barrier, …) son `SAMPLING_PROXY`:
texto fuente observable, no salida del extractor. No son gold; su PPV se
medirá como diagnóstico tras la anotación.

## Lifecycle — relaciones sin material

```text
SUPPLEMENTS 43 / MODIFIES 7   → evaluables si soporte suficiente
CORRECTS / REPLACES / REDEPOSIT → INSUFFICIENT_EVIDENCE (no fabricados)
```
