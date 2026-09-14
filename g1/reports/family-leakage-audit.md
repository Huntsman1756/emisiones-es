# G1-A1 — Family Leakage Audit

`document_family_key` construido solo con evidencia estructural:

```text
CCFF_XXXXX_seq, FOL_XXXXX[.k|-k], FAM_XXXXX_*  ->  PROG_XXXXX
ADM_reg                                      ->  ISSUE_ADM_reg
sin evidencia                                ->  UNKNOWN (no inferido)
```

Nunca por proximidad temporal.

## Colisiones detectadas en el freeze inicial (a4beaf28)

```text
extraction holdout ∩ dev-nuevo   22 familias   (CCFF hermanos no seleccionados)
extraction holdout ∩ G0-dev      23/40 familias
linkage holdout    ∩ dev-nuevo   64 familias
linkage holdout    ∩ G0-dev      30/74
lifecycle holdout  ∩ dev-nuevo   31 familias
lifecycle holdout  ∩ G0-dev      19/34
cold-issuer slice                 0 docs
```

Veredicto del freeze inicial: **FAIL de aislamiento por familia.**

## Resplit G1-A1

La unidad de aislamiento es la familia. Política aplicada:

- Toda familia referenciada por cualquier holdout (extraction, linkage,
  lifecycle, novelty) queda fuera de development.
- Registros hermanos no seleccionados → **quarantine** (ni dev ni holdout).
- Casos G0 que referencian familias holdout → `DEV_RESTRICTED` para trabajo
  sensible a familia (siguen existiendo como dato histórico G0).

```text
después del resplit:
    dev-nuevo ∩ familias holdout      = 0   (assert verificado)
    g0 dev_restricted families        = 45/165
    dev-nuevo docs                    = 331
    quarantined                       = 120
    cold-issuer slice                 = 25/97 docs (3 emisores en cuarentena total)
```

## Cluster concentration (extraction holdout, proxies documentados)

| familia crítica | docs | issuers | familias | objetivo ≥8/≥8 |
|---|---|---|---|---|
| p_callissuer | 23 | 3 | 6 | NO — concentración de mercado |
| p_put | 46 | 5 | 11 | parcial |
| p_basis (day_count) | 41 | 12 | 20 | SÍ |
| p_fixed_rate | 24 | 5 | 8 | parcial |
| p_euribor_rate | 14 | 8 | 10 | SÍ (n bajo) |
| p_barrier | 38 | 2 | 6 | NO — 2 emisores |

La emisión española de estructurados está concentrada (BBVA Global Markets,
Société Générale dominan CCFF estructurados). Esto es una propiedad real del
universo, no del muestreo: los límites se documentan como máximo observable.

## Identidad de familia

```text
familias totales en universo: 480
UNKNOWN: 0  (toda clave deriva de evidencia estructural fuente)
```
