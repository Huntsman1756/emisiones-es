P0 FINAL VERDICT:
FAIL

# P0-F — Final evaluation

Official scoring of the frozen P0-D experiment (60 sealed reviews,
30 crossed paired cases) against the sealed human gold
`truth-human-v1` (`d1f68653…`). Scorer: `p0/score_p0.py` v3
(sealed per `p0/results/p0f/scorer-seal.json`; version history in
`scorer-v1-to-v2.md`). Executed once after seal; two objective
defects were found and corrected under the contract's v1/v2 rule —
both result sets preserved (`v1/`).

## OFFICIAL P0 RESULT

### TIME — FAIL

| metric | value | gate | result |
|---|---|---|---|
| valid paired cases | 30/30 | ≥24 else INCONCLUSIVE | OK |
| median time ratio | **1.387** | ≤ 0.60 | FAIL |
| median time reduction | −38.7% | — | — |
| assisted faster | **7/30** (23.3%) | ≥ 21/30 | FAIL |
| 95% bootstrap CI (paired, seed 20260917, B=10000) | [1.178, 1.745] | upper ≤ 0.80 | FAIL |
| total active time | M 2643 s / A 3441 s | — | — |

ASSISTED was ~39% slower than MANUAL at the median. No gate is close.

### QUALITY — FAIL

| metric | MANUAL | ASSISTED |
|---|---|---|
| precision | 0.429 | **0.430** (gate ≥ 0.99) |
| recall | 0.425 | **0.441** (non-inferiority ok: ≥ M−0.05) |
| completeness | 0.584 | 0.574 |
| TP / FP / FN | 238 / 317 / 322 | 247 / 327 / 313 |

Checks: assisted precision ≥0.99 → FAIL; precision non-inferiority →
PASS; recall non-inferiority → PASS. See "Convention gap" below — the
absolute precision is a lower bound, but the gate fails regardless.

### SAFETY — FAIL

- Assisted critical errors: **119** (gate 0) — FAIL
- Unsupported assisted CONFIRMED: **0** (gate 0) — PASS
- Assisted confirmed with valid evidence: **574/574 = 100%** — PASS

Critical errors concentrate in `redemption` (27), `coupon_type` (26),
`coupon_rate` (21), `call_put_terms` (17), `underlying` (15). A large
share are convention divergences (gold verbatim vs canonical review
values — e.g. `a la par` vs `Par (100%)…`), but under the frozen
definition they are confirmed values disagreeing with gold on critical
fields. On `P0-ADM_123067` both reviewers confirmed one of the two
printed ISINs instead of flagging the document's own conflict
(`FP_CONFLICT_DENIED`) — the independent adjudicator's CONFLICT was
correct and stands.

### EVIDENCE — PASS

- Evidence navigations used: 692 · valid: 692 · **accuracy 100%**
  (gate ≥ 98%)
- Wrong-document links: **0** (gate 0)
- Computed from raw events + decision pointers, not precomputed
  summaries.

### FREEZE INTEGRITY — PASS

All sealed P0-D JSONL files re-hashed against `p0d-seal.json`; human
gold sha + seal self-consistency + expected truth sha
`d1f68653…` verified; ui-freeze tests pass post-run.

## Candidate diagnostics (descriptive only)

- Candidate accept rate 77.0% (245 conf / 73 rej / 0 conflict of 318
  candidate decisions)
- Candidate coverage of human gold: **25.7%** (144/560 confirmed units)
- Manual discoveries: 907 decisions
- Fields confirmed/min: 14.9 · docs opened/review: 0.48 · PDF
  searches/review: 0.00 · evidence jumps/review: 0.38

The sparse candidate coverage means ASSISTED reviewers mostly worked as
manual reviewers with an extra UI — consistent with the time result.

## Slices

By stratum (precision): LOW 0.49 · MEDIUM 0.45 · HIGH 0.36.
By criticality: critical P 0.47 / non-critical P 0.40.
By family: Identity 0.92 · Legal/settlement 0.93 · Issuance 0.60 ·
Coupon 0.25 · Structured payoff 0.13 · Exercise 0.07.
Reviewers: A manual 1452 s / assisted 1710 s (P 0.46); B manual 1191 s /
assisted 1730 s (P 0.40). Both slower assisted; differences do not alter
the verdict.

## P0D-INC-1

`P0-ADM_123092` included as sealed: manual 61.7 s / assisted 191.8 s,
both VALID, pair counted. No exclusion, no correction.

## Convention gap (methodology finding)

`review-schema.json` never specified a value domain. The human
adjudicator recorded verbatim document text; review decisions store the
form's canonical values. scorer-v2 bridges only mechanical
denotations (dates, ISO-4217, number formats, punctuation, consistent
containment); ~a third of confirmed-value disagreements remain that are
representation-level, not factual (e.g. `anualmente` vs `ANNUAL`,
`Fechas de Pago de Cupón (t)` vs `SEMI_ANNUAL`). The scorer does not
adjudicate these — they count as disagreements, so reported
precision/recall are **lower bounds**. The verdict is unaffected: TIME
fails by 2.3× the gate margin and EVIDENCE/FREEZE pass.

## Limitations

- Precision/recall/completeness are conservative lower bounds under the
  residual convention gap; a canonical-value gold would yield higher,
  cleaner numbers but cannot retroactively pass the time gates.
- Timing valid on all 30 pairs; pause events were sub-second.
- No post-hoc sensitivity analysis performed.

## Verdict basis

FAIL on TIME (all three sub-gates), QUALITY (precision < 0.99), SAFETY
(critical errors ≠ 0). PASS on EVIDENCE and FREEZE INTEGRITY. Per
contract: FAIL — no near-pass, no caveats.

Tag: `p0-final-fail`.
