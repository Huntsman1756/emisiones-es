# PROVISIONAL_AGENT_GOLD — reclassification marker

The artifacts in this directory produced under P0-E (commit `a170b57`)
are reclassified as **PROVISIONAL_AGENT_GOLD**:

- `truth-v1.json` — sha256 `57e7dc01f07545f1…`
- `gold-seal.json` — sha256 `94f99f5bf722d6d8…`
- `gold.jsonl`, `gold_cases.jsonl`, `gold-audit.json`

## Material deviations from the frozen gold contract

1. `ADJUDICATOR_C` is an agent, not the independent **human** third
   expert required by the protocol.
2. Bloomberg was used to resolve the underlying ISIN in
   `P0-ADM_123067`; the frozen contract limited gold authority to
   official frozen sources and excluded commercial databases.

## Status

Preserved intact as an auditable artifact. It is **not** the official P0
truth and must not be used for scoring. Official truth will come from
P0-E.1 human adjudication (`truth-human-v1.json`), produced without
access to this gold or to any P0-D output.
