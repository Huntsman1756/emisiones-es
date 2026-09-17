# Gate P0-F — One-shot product scoring

## Verdict: FAIL

```text
scored               60 reviews · 30 paired cases · 1680 field units
gold                 truth-human-v1 (sha d1f68653…) — INDEPENDENT_HUMAN_C
agent gold           excluded from official scoring, per contract
scorer               p0/score_p0.py v3 — seal p0/results/p0f/scorer-seal.json
                     v1→v2→v3 defect record: scorer-v1-to-v2.md (both reported)
bootstrap            paired, seed 20260917, B=10000 (frozen pre-data)

TIME                 FAIL   median ratio 1.387 (gate ≤0.60)
                            assisted faster 7/30 (gate ≥21)
                            CI95 [1.178, 1.745] (upper ≤0.80)
QUALITY              FAIL   assisted precision 0.430 (gate ≥0.99)
                            precision/recall non-inferiority pass
SAFETY               FAIL   critical errors 119 (gate 0)
                            unsupported confirmed 0 · evidence 100%
EVIDENCE             PASS   navigation 692/692 = 100% · wrong-doc 0
FREEZE               PASS   all seals re-verified post-run
```

## Notes

- ASSISTED was ~39% slower at the median — the verdict driver. Machine
  candidates covered only 25.7% of human-gold confirmed units; reviewers
  effectively worked manually with an extra UI (907 manual discoveries).
- Quality/safety absolute numbers are conservative lower bounds: the
  human gold records verbatim document text while the review form stores
  canonical values, and `review-schema.json` never fixed a value domain
  (convention gap documented in `P0-F-FINAL-EVALUATION.md`). Verdict is
  unaffected.
- `P0-ADM_123067`: gold `isin` = CONFLICT preserved; both reviewers
  confirmed one of the printed ISINs → counted as critical error.
- `P0-ADM_123092` (P0D-INC-1): included as sealed, VALID pair.
- Report: `p0/reports/P0-F-FINAL-EVALUATION.md`; raw artifacts +
  `p0f-seal.json` under `p0/results/p0f/` (v1 outputs preserved in
  `p0/results/p0f/v1/`).
- Tag: `p0-final-fail`.
