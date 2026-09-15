# G1-C — ONE-SHOT BLIND EVALUATION

**Verdict: FAIL**

Frozen evaluation of the G1-B.1 code/scoring freeze (`a1da72a`, code
`c1e15f2` tree `13af93ae`) against the four preregistered G1 holdouts,
opened once, no remediation.

## Results

| Evaluation | n | Metric | Verdict |
|---|---|---|---|
| LINKAGE | 124 | P=1.000 (40/40), R=0.588, false_auto=0, forced=0 | **PASS** |
| EXTRACTION | 97 | 5/7 hard gates below threshold; invented=101 | **FAIL** |
| LIFECYCLE | 49 | P=1.000, R=1.000, false edges=0 | **PASS** |
| NOVELTY | 100 | 0.82 ≥ 0.80, CI95 [0.731, 0.890] | **PASS** |
| SAFETY | — | provenance=1.0, unverified=0, invented=101 | **FAIL** |
| FREEZE INTEGRITY | — | all manifests/PDFs/locks verify; 1 documented deviation | **PASS*** |

### Extraction hard gates (truth-v2 canonical)

```text
coupon_rate              0.613  < 0.95   FAIL
day_count                0.875  < 0.95   FAIL
maturity                 1.000  ≥ 0.99   PASS
call_put                 0.900  ≥ 0.90   PASS
reset_fixing             0.793  < 0.90   FAIL
observation              0.767  < 0.90   FAIL
barrier_strike_redemption 0.410 < 0.90   FAIL

provenance               1.000  = 1.00   PASS
invented                   101  > 0      FAIL
unverified                   0  = 0      PASS
```

FAIL under truth-v1 and truth-v2, and under the pre-fix scorer — verdict
robust to all corrections.

## What G1-C established

1. **Linkage architecture generalizes.** Zero false links on 124 unseen
   cases including hard negatives; conservative coverage (59% recall,
   53% review) is a tuning problem, not a correctness problem.
2. **Extraction does not generalize to cold issuers for deep terms.**
   Identity/header fields hold P=1.0 on the 25-doc cold slice; contractual
   recall collapses (coupon_rate R=0.04 cold). The dev-phase P≈1.0 was
   template adaptation to the known corpus.
3. **The product opportunity is real.** 82% of unseen CNMV documents carry
   material document-only content (novelty gate PASS at CI[0.73, 0.89]).
4. **Failure is in value extraction, not location** — PARSING_MISS
   dominates the taxonomy across ~25 fields.

## Deviations (all documented in the final report)

- **DEFECT-EVAL-1**: G1-C scorer stringified dict-valued money
  observations; fixed (evaluation tool, not frozen code); v0 output
  preserved; verdict unchanged.
- **TRUTH v1→v2**: 66 annotation corrections with semantic diff; verdict
  FAIL under both; v2 canonical.
- **DEVIATION-FREEZE-1**: one stale module-hash entry in code-freeze.json
  (never-committed content); integrity independently verified via git
  tree SHA and 18/19 module matches.

## State

```text
G0  FINAL FAIL                        frozen
G1  prereg · AMEND-1/2 · A0 · A · A1 · B · B.1   frozen/PASS
    C  blind evaluation               FAIL (extraction + safety)
```

**Post-verdict:** G1 queda congelado como FAIL permanente (tag
`g1-final-fail`). No se reejecuta ni se remedia sobre los mismos casos.
Los cuatro holdouts G1 están consumidos y pasan íntegros a DEVELOPMENT
para la investigación G2; el holdout G2 será una muestra nueva nunca
vista. Siguiente fase abierta: `docs/gates/G2-A.md`.

Next step is G2 scope definition targeting extraction generalization
(value extraction on cold templates, structured-payoff families,
invented-value suppression). No G2 work initiated here.

Full report: `g1/reports/G1-C-FINAL-EVALUATION.md`
