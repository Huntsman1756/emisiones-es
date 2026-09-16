# Gate P0-E — Blind Gold Adjudication

## Verdict: PASS

```text
cases sealed        30/30
fields per case     28/28
total units         840
critical verified   300/300 (10 per case, independent second check PASS)
evidence contract   satisfied — 0 confirmed values without validated evidence
truth sealed        truth-v1.json sha256 57e7dc01f07545f1…
gold-seal           gold-seal.json sha256 94f99f5bf722d6d8…
review/timing leak  none — P0-D outputs not consulted
```

## Adjudicator

```text
adjudicator          ADJUDICATOR_C (agent — not a human expert)
gold_independence    INDEPENDENT_THIRD_REVIEWER_AGENT
```

Declared deviation from the preferred human third expert: recorded openly
in the seal, the audit and the report. The adjudicator did not perform or
inspect any of the 60 sealed P0-D reviews.

## Status totals

```text
CONFIRMED_VALUE   576
NOT_APPLICABLE    208
MISSING            56
CONFLICT            0
```

## Seal contents (`p0/results/gold/gold-seal.json`)

- truth-v1 SHA-256
- sample manifest SHA-256 (`b12edf37…`)
- review-schema SHA-256
- protocol SHA-256
- 30 source-document SHA-256 (PDF bytes)
- adjudicator identity + independence mode + timestamp

## Consistency checks (all pass)

```text
30/30 cases, 28/28 fields each
valid gold statuses only
evidence present on every CONFIRMED_VALUE and CONFLICT
no duplicate field units (latest-per-field seal semantics)
no unresolved placeholders
all critical units critical_verified=true with second_check PASS
```

## P0D-INC-1

`P0-ADM_123092` adjudicated normally and sealed. The P0-D storage incident
stays in product/workflow scope; it does not affect the economic truth of
the case and is not an exclusion criterion.

## Method constraints honored

- Sources: frozen CNMV PDFs + IR only. No Bloomberg/Refinitiv/commercial
  data, no snippets, no LLM output, no machine candidates as authority.
- Critical fields: independent second check (dual-page excerpt, raw-PDF
  text check, absence scan, or in-page value verification).
- `CONFLICT` count is 0 — no case presented irreconcilable source text;
  the one documentary anomaly found (dual ISIN print for SX7E in
  `P0-ADM_123067`) was resolved by name/Bloomberg code and noted.
- Multi-value fields preserved structure (schedules, hybrid tranches,
  AER tables) per the frozen annotation contract.

## Next

P0-F (one-shot product scoring) is NOT authorized. Nothing is to be
modified between the gold seal and P0-F.
