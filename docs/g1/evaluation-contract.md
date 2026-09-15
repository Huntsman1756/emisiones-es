# G1 Evaluation Contract (congelado en G1-B.1, commit previo a G1-C)

Canonical source: `g1/manifests/scoring-contract.json`. Este documento es la
versión legible; en caso de discrepancia manda el manifest congelado.

## Linkage — denominadores explícitos

Se reportan por separado:

```text
n_all                    todos los casos del linkage holdout
gold_linkable            label=LINK (elegibles para auto-link)
gold_no_link             label=NO_LINK
gold_review_required     label=AMBIGUOUS
pred_auto_linked         decision=AUTO_LINKED
pred_review_required     decision=REVIEW_REQUIRED
pred_no_link             decision=NO_LINK
```

Métricas:

```text
auto_link_precision = AUTO_LINKED correctos / pred_auto_linked      gate >= 0.99
auto_link_recall    = AUTO_LINKED correctos / gold_linkable
auto_link_coverage  = pred_auto_linked / gold_linkable
review_rate         = pred_review_required / n_all
```

`coverage` y `review_rate` NO comparten denominador — por eso pueden sumar >1.
Es correcto por contrato; ninguna métrica llamada `coverage` se reporta sin
denominador declarado.

Hard gates (sin relajar): `false_auto_links = 0`, `forced_links = 0`.

Abstención: `REVIEW_REQUIRED` sobre gold AMBIGUOUS es correcto; sobre gold LINK
es oportunidad perdida (cuenta en recall, no como FP).

## Extraction — por campo

Reporte obligatorio: `positive_gold, TP, FP, FN, precision, recall, coverage,
exact 95% CI binomial, gate_eligible`.

Suficiencia: `<5 INSUFFICIENT_EVIDENCE · 5–14 DESCRIPTIVE_ONLY · >=15 GATE_ELIGIBLE`.
Targets críticos: `coupon_rate_family · day_count · call_put >=20` positivos.

Hard gates de precision (solo si gate_eligible): coupon ≥.95, day_count ≥.95,
maturity ≥.99, call_put ≥.90, reset/fixing ≥.90, observation ≥.90,
barrier/strike/redemption ≥.90.

## Multi-value scoring

Unidad de verdad: el conjunto de elementos gold, definido en el annotation
contract ANTES de anotar.

```text
EXACT               predicted == gold
PARTIAL             predicted ⊂ gold (propio, no vacío)
SUPERSET_WITH_ERROR ≥1 gold correcto + ≥1 candidato sin soporte → FP por candidato
DISJOINT            ningún candidato correcto → FP + FN
MISSING             predicción vacía con gold presente → FN
NOT_APPLICABLE      gold NA y predicción NA
```

`SUPERSET_WITH_ERROR` produce FP. No se concede precision 1.0 porque un
candidato de varios sea correcto — precision es a nivel elemento. Orden
irrelevante. Aspectos complementarios legítimos (componentes de fixing,
componentes de redemption, regímenes de cupón) se anotan como elementos gold
separados.

## ExerciseTerms

Vista legacy `call_dates`/`put_dates` para thresholds preregistrados;
evaluación estructural (option_side, dates/window, price, notice, conditions)
como diagnóstico separado.

## Structured products

Sin `barrier` plano como verdad única. Se evalúan por separado:
`autocall_trigger`, `coupon_barrier`, `protection_barrier`, `strike`,
`participation`, `cap`, `observation_schedule`. El threshold
`barrier/strike/redemption ≥.90` se aplica por rol si gate_eligible.

## Classification

Dos categorías reportadas desagregadas:

- `METADATA_DETERMINED` — rol desde metadata estructurada CNMV. Éxito válido
  de clasificación, pero demuestra determinismo del contrato, no generalización.
- `CONTENT_DETERMINED` — rol desde título/anchors/firmas del contenido.

Reportadas: `role_accuracy_overall`, `metadata_determined_accuracy`,
`content_determined_accuracy`, `unknown_rate`, `false_confident_rate`.
Sin nuevo hard threshold.

## Lifecycle

Gate-eligible: SUPPLEMENTS, MODIFIES. `CORRECTS/REPLACES/REDEPOSIT` =
INSUFFICIENT_EVIDENCE (ni PASS ni FAIL). Hard gate: false-positive edge = 0.
Abstención ante evidencia insuficiente = correcto.

## Novelty

Solo `novelty-holdout` SRS n=100 (seed 20260917). Estimador directo + IC
binomial exacto 95%. Gate ≥80%. Gold independiente del extractor
(documento + novelty-field-map + disponibilidad FIRDS/ESAP/CNMV).
El extraction challenge holdout NO estima prevalencia.

## Safety

`provenance = 100%`, `invented = 0`, `false_auto = 0`, `forced = 0`. Sin relajar.

## Blind truth

Preferido: seal predictions → hash → gold sin ver predictions → seal truth →
score. Alternativa: truth-first con anotador ciego a outputs.

## Truth corrections

Errata objetiva → `truth-v1`/`truth-v2` + diff + evidence + reason + dirección
de impacto. Máximo un proceso formal antes del verdict. Si afecta hard gates,
verdict bajo ambas versiones.

## Retry

Solo crash / I/O transient / interrupción de recurso / output corrupto.
Nunca por mal resultado. First attempt preservado.
