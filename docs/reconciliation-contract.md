# Contrato de reconciliación (G0-C)

Primitiva: `reconcile(field, subject_key, observations)` en
`src/emissions_es/reconciliation/`.

Estados `ReconciliationStatus`:

| Estado | Condición |
|---|---|
| `AGREE` | todas las observaciones normalizadas son iguales |
| `CONFLICT` | hay valores distintos — **todas se conservan** |
| `SOURCE_ONLY` | una sola fuente observó el campo |
| `MISSING` | ninguna fuente observó el campo |
| `NOT_APPLICABLE` | el campo no aplica al instrumento |

Reglas:

- Nunca se selecciona silenciosamente "la mejor fuente": un CONFLICT
  mantiene los `TermObservation` originales con su evidencia completa.
- Las observaciones `MISSING` se conservan en el registro pero no
  cuentan como valor.
- Fixtures de demostración: `tests/test_core_g0c.py` (`same ISIN +
  same maturity -> AGREE`; `maturity A vs B -> CONFLICT`).

Un `CONFLICT` de extracción intra-documento (p.ej. cupón fijo inicial +
variable en prórroga, caso Y04 scout) no es un error del extractor: es
la representación honesta de un instrumento con regímenes múltiples.
La resolución a nivel de instrumento corresponde a fases posteriores
(fuera de G0-C).
