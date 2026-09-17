# Scorer v1 → v2 — objective defect record

Per P0-F contract §14: defects in the sealed scorer may be fixed with
version history preserved. Both result sets are reported (v1 under
`p0/results/p0f/v1/`).

## Versions

| version | file | sha256 |
|---|---|---|
| v1 (sealed) | `p0/scorer_versions/scorer-v1.py` | `c82dc1b6f0465352ee081b0b0513b60eaafbd0cc98ecc3781144dbd9738a6fc0` |
| v2 | see `scorer-seal.json` `versions[1]` | value-equivalence layer (superseded) |
| v3 | `p0/score_p0.py` | see `scorer-seal.json` `versions[2]` |

Diffs: `scorer-v1-to-v2.diff`; v2→v3 is the `quality_scores`
family-mapping fix below (cosmetic to verdict, reported per contract).

## Defect 1 — timing_status not in sealed format

**Reason:** scorer-v1 read `timing_status` from `reviews.jsonl` rows. The
sealed P0-D artifacts predate the field (added to `p0/app/store.py` in the
hardening commit *after* P0-D was sealed), so every pair scored
`None` → invalid → spurious `TIME: INCONCLUSIVE`.

**Fix:** `timing_status_from_events()` recomputes the frozen rule from
sealed `events.jsonl` (`CASE_PAUSED` without resume/submit within 300 s
→ `INVALID_TIMING`), mirroring `store.py` submission logic exactly.

**Impact:** v1 → all 30 pairs invalid. v2 → 30/30 valid pairs (two real
sub-second pauses, none >5 min). Timing is now measured per protocol.

## Defect 2 — literal string equality is not semantic comparison

**Reason:** the frozen review-schema defines no canonical value domain.
The human gold records verbatim document text (`"Euros"`,
`"17 de julio de 2020"`, `"4.35%"`), while review decisions store the
form's canonical values (`"EUR"`, `"2020-07-17"`, `"4.35% of the initial
nominal investment, …"`). Literal equality marked ~76% of confirmed
observations wrong — a representation artifact, not human error.

**Fix:** `value_equal` now applies *mechanical denotation equivalences
only*: NFKC/casefold/whitespace, ES/EN date parsing → same date,
ISO-4217 currency-name mapping, ES/EN numeric formats, punctuation-
insensitive alnum equality (`ACT/ACT (ICMA)` ≡ `ACT_ACT_ICMA`), and
containment when numeric content is consistent (`"4.35%"` inside
`"4.35% of the initial nominal investment…"`).

**Explicit boundary — no translation/synonymy.** Where gold recorded a
document label or a natural-language term that no mechanical rule
bridges to the review's canonical code (e.g. `payment_frequency` gold
`"Fechas de Pago de Cupón (t)"` vs `"SEMI_ANNUAL"`; `"anualmente"` vs
`"ANNUAL"`; `"fijo"` vs `"0,875% nominal anual…"`), v2 keeps the
mismatch. These are convention divergences in the gold annotation, not
demonstrable reviewer errors — but the scorer does not adjudicate them.
They are counted as disagreements (conservative for the product) and
reported per-field in `quality-score.json` so the residual is visible.

**Impact:** precision/recall rise from ~0.16 to the values in the v2
`quality-score.json`; the residual per-field breakdown quantifies the
unresolved convention gap. The final verdict is unaffected: TIME fails
by a wide margin under either scorer.

## Defect 3 (v3) — field-family grouping

**Reason:** `quality_scores` indexed `FIELD_FAMILIES` as if it were
`{field: family}`, but it is `{family: [fields]}`; every field fell into
`Other`. Reporting-only defect — no gate uses family slices.

**Fix:** build the reverse map. **Impact:** `by_field_family` now splits
correctly; verdict and all gates unchanged.

## What did NOT change

- Protocol gates, thresholds, bootstrap constants (seed 20260917,
  B=10000), state model, multi-value strictness, critical-field list,
  seal verification, evidence validation, warmup exclusion.
- P0-ADM_123067 gold `CONFLICT` handling; P0-ADM_123092 included as-is.
