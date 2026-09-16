# P0-D — Official timed blind reviews — COMPLETED (sealed, unscored)

## Result

```text
REVIEWER_A   30/30 DONE   15 MANUAL / 15 ASSISTED
REVIEWER_B   30/30 DONE   15 MANUAL / 15 ASSISTED

reviews              60/60 submitted
closeouts            60/60 written
unresolved critical  0
broken evidence      0
wrong-document       0
UI_ERROR             0
jsonl malformed      0 (post-recovery)
```

## Sealed artifacts

Runtime (authoritative): `p0/runtime/p0d_77711e42/` (A) and `p0/runtime/p0d_2afdc603/` (B).

Results copies: `p0/results/p0d/reviewer_a/` and `p0/results/p0d/reviewer_b/`.

Seal manifest: `p0/results/p0d/p0d-seal.json` — SHA-256 per JSONL (events, decisions,
intervals, reviews, closeouts) + session seals + incident log.

## Integrity verification

- `reviews.jsonl`: 30 unique cases per reviewer, no duplicates, no missing.
- `closeouts.jsonl`: 1 per submitted case; all derived fields populated.
- `events.jsonl`: monotonic timestamps; every case has CASE_OPENED + CASE_SUBMITTED.
- `decisions.jsonl`: all lines parse; re-decided fields are normal reviewer
  corrections (last decision per field wins, per store semantics).
- Session-file SHA vs pre-review seal differs as designed — the server writes
  `status: DONE` back into the session file on each submit.
- `ui-freeze-final.json` (afc0991f53…) unchanged; no code touched during P0-D.
- Candidate/graph/sample/assignments/protocol/schema hashes unchanged.

## Incident P0D-INC-1 — STORAGE_INTEGRITY (logged, not fixed)

Case `P0-ADM_123092` (REVIEWER_B, ASSISTED): chained manual saves produced
truncated JSONL lines server-side. The reviewer recovered, re-entered the
affected fields, and annotated it in UX notes. Post-hoc verification:

- all JSONL parses cleanly;
- lifecycle complete and monotonic;
- exactly 1 review + 1 closeout for the case;
- 0 sealed decisions lost;
- two `CASE_SUBMITTED` intervals recorded — `active_seconds` covers both
  active periods, which is faithful to what happened.

Classified as `STORAGE_INTEGRITY` / `TECHNICAL_CRASH`-adjacent instrumentation
issue. Per protocol: registered only, no patch during the phase. Candidate for
a post-P0 hardening fix (atomic/rotating JSONL writes).

## Discipline maintained

```text
product logic changes   0
metric calculations     0
cross-reviewer compare  0
gold construction       0 — STOPPED HERE per protocol
scoring                 0
```

## Next (requires separate authorization)

Gold adjudication + scoring per `p0/manifests/protocol.json` §criteria.
