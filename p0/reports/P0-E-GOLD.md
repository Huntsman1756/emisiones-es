# P0-E — Blind Gold Adjudication

## Scope

30 holdout cases × 28 schema fields adjudicated exclusively from frozen
source documents (CNMV PDFs + IR evidence). No P0-D review output, timing,
mode, candidates or aggregate metrics were consulted during adjudication.

## Adjudicator

- `ADJUDICATOR_C` — **agent** (Devin), not a human expert.
- `gold_independence = INDEPENDENT_THIRD_REVIEWER_AGENT`: the adjudicator
  did not perform any of the 60 P0-D reviews and did not open them.
- Registered explicitly as agent adjudication; this distinction is carried
  into the gold seal and must not be hidden in the final report.

## Method

Each of the 840 units was recorded through `p0/record_gold.py` →
`p0.app.gold.GoldStore`:

- `evidence.validate_pointer` — the same validation path as reviewer
  submissions — applied to every evidence pointer (doc, sha, page, excerpt,
  bbox when the IR box is geometrically valid; page+excerpt retained when
  the IR block had an invalid/mixed-origin bbox).
- Every `CONFIRMED_VALUE` carries at least one validated evidence pointer.
- Every one of the 10 CRITICAL fields in every case carries a passing
  independent second check (`value_in_page`, `dual_excerpt` across distinct
  pages, `absence_scan`, or `pdf_text_check` — raw PDF text via pypdfium2,
  independent of the Docling IR).
- Absent or irrelevant fields were recorded as `MISSING` / `NOT_APPLICABLE`
  rather than inferred.

## Consistency results

- 30/30 cases sealed · 28/28 fields each · 840 units total.
- Status totals: CONFIRMED_VALUE 576 · NOT_APPLICABLE 208 · MISSING 56 ·
  CONFLICT 0.
- All 300 critical units (30 cases × 10 critical fields) verified with a
  passing second check.
- No confirmed value without evidence; no duplicate field units; no
  unresolved placeholders.

## Annotation issues and ambiguities (recorded in adjudication notes)

- `P0-ADM_123067`: the document prints two different ISINs for the
  EuroStoxx Banks underlying (EU0009658426 / EU0009658145) — issuer typo;
  identity is unambiguous by name + Bloomberg code (SX7E). Confirmed by
  name/code with note.
- `P0-ADM_123019`, `P0-ADM_124130`: hybrid structures (85% fixed leg
  mandatorily redeemed early + 15% autocallable tranche) — recorded with
  multi-part values preserving both legs.
- `P0-ADM_123067`: redemption below barrier is leveraged
  (`IN × PF/(70%×PI)`), not the more common `PF/PI`; recorded verbatim.
- `P0-ADM_123045`: initial price fixed on 5-Jul-2017 (the exchanged
  issue's strike date), ~3 years before this issue.
- `P0-ADM_120969`: IR lost the coupon rate token ("per cent." without the
  number); the value was confirmed via `pdf_text_check` on the raw PDF and
  the issue summary.
- `ranking`/`subordination` are `MISSING` in the Bankinter structured FTs —
  the documents refer to the Base Prospectus securities note, not included
  in the case; no inference was made.
- `P0D-INC-1` (`P0-ADM_123092`): adjudicated normally. The storage
  incident belongs to product/workflow scope, not truth scope.

## Deviations

- Adjudicator is an agent rather than a human third expert — declared in
  `gold_independence`.
- Some IR table blocks have invalid bounding boxes; affected pointers keep
  validated page+excerpt evidence without bbox (intentional, documented in
  `p0/record_gold.py`).

## Artifacts

- `p0/results/gold/truth-v1.json` — sha256 `57e7dc01f07545f1…`
- `p0/results/gold/gold-seal.json` — sha256 `94f99f5bf722d6d8…`
- `p0/results/gold/gold-audit.json`
- `p0/results/gold/gold.jsonl`, `gold_cases.jsonl`, per-case JSONs
- `p0/record_gold.py`, `p0/app/gold.py`, `p0/build_truth.py`

## Not done

No scoring. No MANUAL vs ASSISTED comparison. No P0-D results opened.
P0-F remains unauthorized.
