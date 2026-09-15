# G1-C — ONE-SHOT BLIND EVALUATION — FINAL REPORT

**Verdict: FAIL** (extraction hard gates + invented-values safety gate)

- HEAD: `a1da72a` (pre-flight OK; src tree clean)
- Code freeze: `g1/manifests/code-freeze.json` (`7e24bfe7…`)
- Scoring contract: `g1/manifests/scoring-contract.json` (`efc79371…`)
- Frozen code commit verified: `c1e15f2`, tree `13af93ae…` (git-verified byte-identical)

## Executive summary

| Evaluation | n | Result | Verdict |
|---|---|---|---|
| LINKAGE | 124 | P=1.000 R=0.588, false_auto=0, forced=0 | **PASS** |
| EXTRACTION | 97 | 5/7 hard gates fail; invented=101 | **FAIL** |
| LIFECYCLE | 49 | P=1.000 R=1.000, FP=0 | **PASS** |
| NOVELTY (SRS) | 100 | 82% ≥80%, CI95[0.731, 0.890] | **PASS** |
| SAFETY/PROVENANCE | — | provenance=1.0, unverified=0, **invented=101** | **FAIL** |
| FREEZE INTEGRITY | — | all checks OK, 1 documented deviation | **PASS*** |

\* DEVIATION-FREEZE-1 below: one module-hash entry in `code-freeze.json`
records a value never committed; integrity verified independently via git
tree SHA, clean `src/`, and 18/19 matching module hashes.

**G1-C is FAIL.** The decisive failures are the extraction hard gates and
the `invented=0` safety gate. No "near pass" is claimed.

---

## 1. OFFICIAL RESULTS

### 1.1 LINKAGE — n=124 — `g1/results/linkage-score.json`

Predictions sealed before gold reveal: `770ac355…`

```text
n_all                  124
gold_linkable           68   gold_no_link        30   gold_review  26
pred_auto_linked        40   pred_review         66   pred_no_link 18

AUTO_LINK precision     1.0000  (40/40)
AUTO_LINK recall        0.5882  (40/68; denominator = gold_linkable)
AUTO_LINK coverage      0.5882  (same denominator)
review_rate             0.5323  (66/124; denominator = n_all)

false_auto_links        0      HARD GATE PASS
forced_ambiguous        0      HARD GATE PASS
```

Every AUTO_LINKED case was a correct L1 explicit-family link. The linker is
strictly conservative: it refuses 28/68 linkable cases into REVIEW_REQUIRED
rather than risking a false link. All 15 L6 hard negatives were held at
REVIEW/NO_LINK — zero false positives on adversarial cases.

Per-stratum decisions (`label->decision`):

| Stratum | Outcome |
|---|---|
| L1 explicit_family | 40 LINK→AUTO_LINKED |
| L2 supplement→base | 18 LINK→REVIEW_REQUIRED |
| L3 role_collision | 10 LINK→REVIEW_REQUIRED |
| L4 same-issuer-multi-programme | 14 NO_LINK→REVIEW, 1 NO_LINK→NO_LINK |
| L5 missing_family | 16 AMBIGUOUS→NO_LINK |
| L6 hard_negative | 15 NO_LINK→REVIEW |
| L7 succession | 9 AMBIGUOUS→REVIEW, 1 AMBIGUOUS→NO_LINK |

Diagnostic taxonomy: dominant failure class is under-linking into
REVIEW_REQUIRED on L2/L3 — explicit-reference coverage, not false evidence.
No RULE_DEFECT observed; no NEGATIVE_EVIDENCE_MISSED.

### 1.2 EXTRACTION — n=97 — `g1/results/extraction-score.json` (truth-v2, canonical)

Predictions sealed: `f1ccf6ae…`. Truth-v1 sealed `ff69dcdc…` before scoring.
Canonical score uses truth-v2 (`622b5980…`); see §3 for the correction trail.

**Hard gates (frozen thresholds, exact per scoring-contract):**

| Family | threshold | pos_gold | tier | precision | verdict |
|---|---|---|---|---|---|
| coupon_rate | 0.95 | 70 | GATE_ELIGIBLE | 0.6129 | **FAIL** |
| day_count | 0.95 | 63 | GATE_ELIGIBLE | 0.8750 | **FAIL** |
| maturity | 0.99 | 93 | GATE_ELIGIBLE | 1.0000 | PASS |
| call_put | 0.90 | 41 | GATE_ELIGIBLE | 0.9000 | PASS |
| reset_fixing | 0.90 | 62 | GATE_ELIGIBLE | 0.7931 | **FAIL** |
| observation | 0.90 | 41 | GATE_ELIGIBLE | 0.7667 | **FAIL** |
| barrier_strike_redemption | 0.90 | 131 | GATE_ELIGIBLE | 0.4104 | **FAIL** |

**Safety:** provenance=1.0 (1298 accepted observations, 0 violations) PASS;
value_unverified=0 PASS; **invented=101 FAIL** (predictions emitted on
ABSENT-gold fields; top fields: redemption_formula 31,
business_day_convention 23, ranking 18 — mostly template/boilerplate
emission on FOL/CCFF docs).

**Per-field (P / R / CI95 on precision):**

| field | pos | TP | FP | FN | P | R | CI95 P |
|---|---|---|---|---|---|---|---|
| isin | 89 | 84 | 0 | 5 | 1.000 | 0.944 | [0.957, —] |
| currency | 97 | 70 | 0 | 27 | 1.000 | 0.722 | [0.949, —] |
| issue_date | 89 | 70 | 0 | 19 | 1.000 | 0.786 | [0.949, —] |
| maturity | 93 | 56 | 0 | 37 | 1.000 | 0.602 | [0.936, —] |
| denomination | 96 | 70 | 0 | 26 | 1.000 | 0.729 | [0.949, —] |
| issued_amount | 97 | 37 | 1 | 60 | 0.974 | 0.381 | [0.862, 0.999] |
| coupon_type | 88 | 53 | 1 | 35 | 0.982 | 0.602 | [0.901, 1.000] |
| coupon_rate | 70 | 19 | 12 | 57 | 0.613 | 0.250 | [0.422, 0.782] |
| benchmark | 35 | 13 | 12 | 23 | 0.520 | 0.361 | [0.313, 0.722] |
| spread | 25 | 3 | 4 | 22 | 0.429 | 0.120 | [0.099, 0.816] |
| payment_frequency | 74 | 31 | 23 | 48 | 0.574 | 0.392 | [0.432, 0.708] |
| day_count | 63 | 42 | 6 | 28 | 0.875 | 0.600 | [0.748, 0.953] |
| call_dates | 37 | 26 | 1 | 16 | 0.963 | 0.619 | [0.810, 0.999] |
| business_day_convention | 55 | 27 | 55 | 31 | 0.329 | 0.466 | [0.229, 0.442] |
| put_dates | 4 | 1 | 2 | 3 | 0.333 | 0.250 | INSUFFICIENT_EVIDENCE |
| reset_dates | 24 | 3 | 0 | 21 | 1.000 | 0.125 | [0.292, —] |
| fixing_rules | 38 | 20 | 6 | 18 | 0.769 | 0.526 | [0.564, 0.910] |
| ranking | 15 | 3 | 18 | 12 | 0.143 | 0.200 | [0.031, 0.363] |
| subordination | 32 | 16 | 3 | 16 | 0.842 | 0.500 | [0.604, 0.966] |
| redemption_formula | 61 | 47 | 64 | 14 | 0.423 | 0.770 | [0.330, 0.521] |
| underlying | 67 | 30 | 47 | 42 | 0.390 | 0.417 | [0.281, 0.508] |
| barrier | 42 | 23 | 15 | 48 | 0.605 | 0.324 | [0.434, 0.760] |
| autocall | 23 | 1 | 23 | 32 | 0.042 | 0.030 | [0.001, 0.211] |
| observation_dates | 41 | 46 | 14 | 31 | 0.767 | 0.597 | [0.640, 0.866] |
| settlement_type | 95 | 54 | 14 | 41 | 0.794 | 0.568 | [0.679, 0.883] |
| participation | 5 | 0 | 1 | 5 | 0.000 | 0.000 | DESCRIPTIVE_ONLY |
| cap | 2 | 0 | 3 | 2 | 0.000 | 0.000 | INSUFFICIENT_EVIDENCE |
| strike | 5 | 0 | 0 | 5 | 0.000 | 0.000 | DESCRIPTIVE_ONLY |

Support targets (≥20 positives desired): coupon_rate 70, day_count 63,
call_put 41 — all reached GATE_ELIGIBLE as preregistered.

**Failure taxonomy** (from scorer): overwhelmingly `PARSING_MISS` — fields
are located but the value is not extracted/normalized (issued_amount 57,
coupon_rate 47, maturity 37, currency 27 …). Only ~12 `LOCATION_MISS`
events total. The failure concentrates in the value-extraction stage, not
in region location.

**COLD_ISSUER slice (25/97) vs SEEN (72/97)** — diagnostic only:

| field | cold P | cold R | seen P | seen R |
|---|---|---|---|---|
| isin | 1.00 | 0.88 | 1.00 | 0.97 |
| currency | 1.00 | 0.72 | 1.00 | 0.72 |
| maturity | 1.00 | 0.77 | 1.00 | 0.55 |
| denomination | 1.00 | 0.72 | 1.00 | 0.73 |
| issued_amount | 0.94 | 0.68 | 1.00 | 0.28 |
| coupon_rate | 1.00 | **0.04** | 0.60 | 0.38 |
| day_count | 0.33 | 0.14 | 0.91 | 0.65 |
| call_dates | 0.67 | 0.14 | 1.00 | 0.86 |
| business_day_convention | 0.00 | 0.00 | 0.34 | 0.66 |
| redemption_formula | 0.79 | 0.68 | 0.35 | 0.82 |
| underlying | 0.14 | 0.21 | 0.53 | 0.49 |
| barrier | 0.11 | 0.05 | 0.76 | 0.43 |
| settlement_type | 0.28 | 0.20 | 0.98 | 0.70 |

Identity/header fields generalize (CNMV templates are uniform); deep
contractual terms collapse on unseen issuers — evidence of template-layout
learning rather than transferable semantics for the deep-term families.

**Classification diagnostics:** role_accuracy=0.9691 (97 docs),
METADATA_DETERMINED n=97 acc=0.9691, CONTENT_DETERMINED n=0,
unknown=0, false_confident=3. As preregistered, this measures contract
determinism on CNMV structured metadata, not document inference.

### 1.3 LIFECYCLE — n=49 — `g1/results/lifecycle-score.json`

Predictions sealed `fb8f9293…`. SUPPLEMENTS edges: TP=49, FP=0, FN=0,
P=1.0, R=1.0. false-positive lifecycle edges=0 — HARD GATE PASS.
CORRECTS/REPLACES/REDEPOSIT remain INSUFFICIENT_EVIDENCE per preregistration;
not evaluated as pass/fail.

### 1.4 NOVELTY — n=100 SRS (seed 20260917) — `g1/results/novelty-score.json`

Gold built independently of extractor output; truth sealed `78ccfcb6…`.

```text
novelty_true   82 / 100
rate           0.82     HARD GATE >= 0.80: PASS
exact CI95     [0.7305, 0.8897]
```

Gold criterion: `has_material_document_only_delta` vs frozen
novelty-field-map + structured-upstream availability. Documents whose only
term-bearing content is already in structured feeds (or template text)
score FALSE; documents publishing real contractual/registrable terms not
upstream-available score TRUE. Product-level finding: ~82% of CNMV corpus
documents carry material document-only content — the document-graph +
field-provenance layer has differentiated value vs FIRDS/ESAP structure.

---

## 2. PERFORMANCE — `g1/results/performance.json`

| metric | p50 | p90 | p95 | max | total |
|---|---|---|---|---|---|
| Docling conversion (s) | 48.56 | 234.37 | 424.69 | 880.42 | 9483.22 |
| Extraction (s) | 0.05 | 0.58 | 1.13 | 13.19 | 33.19 |
| peak RSS (MB) | 41.2 | 234.5 | 807.5 | 1152.9 | — |
| pages/doc | 10 | 103 | — | 276 | 3067 |

KEEP_FULL as frozen; no optimization attempted during G1-C.

---

## 3. DEVIATIONS AND CORRECTIONS (audit trail)

### DEFECT-EVAL-1 — scorer value normalization (evaluation-tool defect)

`tools/g1c_score_extraction.py` was written during G1-C (untracked
evaluation tooling; NOT part of the frozen `src/` tree). Its `norm()`
applied `str(v)` to all values; money observations serialize as
`{'amount','currency','raw_number'}` dicts, so `str(dict)` produced
unmatchable lexemes — denomination/issued_amount showed false P≈0.05.
The frozen contract requires comparing "the same normalized value";
stringifying a dict is an implementation defect, not contract semantics.

Fix applied (documented, one change): dicts with `amount` normalize to the
numeric amount; numeric strings canonicalize (`2.50`==`2.5`,
`100.00`==`100`); non-money lexemes unchanged. Scorer also accepts
explicit truth/output paths.

Outputs preserved separately:

| artifact | scorer | truth | sha256 (prefix) |
|---|---|---|---|
| `extraction-score-v0-dictnorm-defect.json` | defective | v1 | `60203b41…` |
| `extraction-score-v1.json` | corrected | v1 | `7a76a687…` |
| `extraction-score.json` (canonical) | corrected | v2 | `f13f94f3…` |

Verdict is FAIL under all three — the defect correction does not alter the
gate outcome (5/7 gates fail in every version).

### TRUTH-V1 → TRUTH-V2 — annotation errata (formal correction process #1)

After scoring, objective annotation errors were identified against
document evidence (truth is hand-verified; errors were form/canonical
mismatches, not pred-derived). Per the frozen protocol, truth-v1 was NOT
overwritten; truth-v2 + semantic diff were generated:

- `extraction-truth-v2.json` sha256 `622b5980…`
- `extraction-truth-v1-v2-diff.json` sha256 `9cbb2e3f…` — **66 changes**

Categories: (a) day-count MULTI labels where documents publish two
legitimate regimes (e.g. ACT/ACT ICMA + ACT/360); (b) benchmark tenor
corrected to literal published tenor (EURIBOR 3m/6m/12m variants);
(c) subordination corrected to literal contractual designation
(senior preferred/non-preferred, tier 2); (d) fixing_rules and
observation_dates ABSENT→PRESENT where schedules are explicitly published;
(e) payment_frequency multi-regime (regular + extension coupons);
(f) underlying added where defined. `CCFF_11289_001` kept ABSENT — no
status declared; "not found" is valid.

Verdict reported under both versions: **FAIL under v1 and v2** → single
verdict; v2 is canonical.

### DEVIATION-FREEZE-1 — one module hash in code-freeze.json

Post-run freeze verification found `code-freeze.json.modules
['extraction/common'] = 91709a13…` matches no file: `common/__init__.py`
is `9fcf3268…` in c1e15f2 (frozen code), a1da72a, and the working tree —
git history contains exactly one blob for the path. The recorded hash was
generated from a transient working-tree state during G1-B.1 freeze
generation and was never committed. It is a **freeze-record defect**, not
a code-integrity violation: integrity is independently verified by
`git.tree = 13af93ae` (= `c1e15f2^{tree}`, byte-exact for all of src/),
`git status` clean on `src/`, and 18/19 module hashes matching. Also note
`tools/g1c_freeze_verify.py` maps the four package extractors to stale
`.py` paths; verified manually against `*/__init__.py` — all match.

All other freeze checks pass: 4 holdout manifests, family-map,
novelty-holdout, annotation-contract, development, freeze.json,
requirements-lock, pyproject, and 196 referenced PDFs (sha_fail=[],
missing=[]).

### Retry policy

No retries were performed for quality reasons. Docling conversion ran in
slices; all outputs are first attempts on identical input bytes.

---

## 4. FREEZE VERIFICATION (before/after)

| check | before | after |
|---|---|---|
| src tree | `13af93ae` (c1e15f2) | `13af93ae` — unchanged |
| git status src/ | clean | clean |
| code-freeze.json sha | `7e24bfe7…` | `7e24bfe7…` — unchanged |
| scoring-contract sha | `efc79371…` | `efc79371…` — unchanged |
| 4 holdout manifests | frozen hashes | verified — unchanged |
| holdout PDFs | 196 sha verified | 196 sha verified — unchanged |
| tests | 65/65 PASS | — |

## 5. OFFICIAL vs POST-HOC ANALYSIS

The above is the OFFICIAL evaluation. Post-hoc product analysis (not part
of the verdict):

1. **Extraction generalization is the core gap.** Dev showed P≈1.0 across
   families; holdout shows the architecture does NOT generalize to unseen
   issuer layouts for deep contractual terms. The dev result was
   template adaptation to the G0 corpus — exactly the risk G1-C was
   designed to detect.
2. **Locate-then-extract locates; the failure is value extraction.**
   Failure taxonomy is dominated by PARSING_MISS (~25 fields), not
   LOCATION_MISS. Regions are found; value emission/normalization fails.
3. **Precision remains high where the extractor emits** (identity fields
   P=1.0, call_dates 0.963, reset_dates 1.0) — the abstain+verify design
   holds; the missing capability is coverage of deep terms.
4. **Linkage is production-shaped**: zero false links at 59% recall —
   conservative but correct; raising recall on L2/L3 is G2 work.
5. **Novelty 82% confirms the product hypothesis**: most CNMV documents
   carry document-only contractual content; the gap is extraction
   quality, not opportunity.
6. **Structured-product fields are weakest** (autocall P=0.04,
   barrier_strike_redemption P=0.41) — the family needs dedicated
   structured-payoff extraction, not table flattening.

## 6. ARTIFACT INDEX

| artifact | sha256 (prefix) |
|---|---|
| `extraction-predictions.json` (sealed) | `f1ccf6ae…` |
| `extraction-truth-v1.json` (sealed) | `ff69dcdc…` |
| `extraction-truth-v2.json` (canonical) | `622b5980…` |
| `extraction-truth-v1-v2-diff.json` | `9cbb2e3f…` |
| `extraction-score-v0-dictnorm-defect.json` | `60203b41…` |
| `extraction-score-v1.json` | `7a76a687…` |
| `extraction-score.json` (canonical) | `f13f94f3…` |
| `extraction-slices.json` (diagnostic) | — |
| `linkage-predictions.json` (sealed) | `770ac355…` |
| `linkage-score.json` | `89d68ccb…` |
| `lifecycle-predictions.json` (sealed) | `fb8f9293…` |
| `lifecycle-score.json` | `b7210ab4…` |
| `novelty-truth.json` (sealed) | `78ccfcb6…` |
| `novelty-score.json` | `acead909…` |
| `provenance-score.json` | — |
| `classification-score.json` | — |
| `performance.json` + docling slices | — |
