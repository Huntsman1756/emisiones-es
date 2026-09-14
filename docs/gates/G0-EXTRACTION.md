# G0-C/D — Corpus de extracción + ablación determinista

## Corpus (n ≈ 30, heterogeneidad > representatividad)

Composición propuesta (preregistrada en `g0/manifests/corpus-proposal.md`;
la lista concreta de documentos se congela al descargar):

| Estrato | n propuesto | Fuente típica |
|---|---|---|
| Bonos simples senior (plain vanilla) | 5 | CCFF AIAF de bancos grandes |
| FRN (Euribor + spread) | 4 | CCFF AIAF/MARF |
| Cédulas/covered bonds | 4 | Folleto base + CCFF |
| Subordinados T2 | 2 | Folleto/condiciones |
| AT1 (contingentes convertibles) | 2 | Folleto + CCFF (docs EN frecuentes) |
| Productos estructurados (autocall/barrera) | 5 | "Bonos/oblig. estructurados" AIAF |
| Suplementos | 3 | — |
| Correcciones / redepósitos | 2 | — |
| Multi-venue | 2 | AIAF+MARF o dual |
| Portfolio Stock Exchange | 1–2 | Documento informativo de incorporación |
| SECURITIZE / DLT | 0–1 | Si no hay emisión pública: design-case con reglamento + autorización |
| **Total** | **≈30** | |

Selección prioriza heterogeneidad de formato (plantillas CCFF de distintos
emisores, folletos únicos vs programme-based) sobre frecuencia real.

## Dominio de campos (cada extractor declara su dominio)

Grupo A (todos los deuda): `issue_date, maturity, currency, denomination,
issued_amount, coupon_type, coupon_rate, benchmark, spread,
payment_frequency, day_count, business_day_convention, ranking,
subordination`.

Grupo B (condicionales): `reset_dates, fixing_rules, call_dates, put_dates,
redemption_formula`.

Grupo C (estructurados): `underlying, strike, barrier, participation, cap,
autocall, observation_dates, settlement_type`.

## Métricas preregistradas por tipo de campo

```text
coupon/rate precision            >= 95%
day-count                        >= 95%
maturity                         >= 99%
call/put schedules               >= 90%
reset/fixing                     >= 90%
structured observation dates     >= 90%
barrier/strike/redemption        >= 90%
```

Recall medido por campo; sin media global que esconda campos difíciles.

## Ablación

Por tier: `documents_escalated, pages_escalated, fields_recovered,
precision_delta, recall_delta, runtime, CPU, peak_RAM`.
Cualquier tier sin mejora marginal demostrada se elimina del diseño.
