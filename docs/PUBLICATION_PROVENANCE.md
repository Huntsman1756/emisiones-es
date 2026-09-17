# Publication provenance

This repository is a **sanitized export** of the private canonical
research repository `emisiones-es` (kept private; contains the full
research history including the CNMV corpus paths).

```text
canonical pre-publication HEAD:  ae37618 ("R0: preserve frozen IR
                                 adapter in tools/repro/ (post-evaluation)")
canonical final tag:             p0-final-fail
export HEAD (rewritten):         this commit's parent line; history was
                                 rewritten by git filter-repo, so commit
                                 SHAs differ from the canonical line
reason for history sanitization: publication-policy breach fixed in the
                                 working tree by commit "50bd311" was
                                 still recoverable from history — the
                                 project's own conservative policy
                                 (docs/licensing.md) is not to
                                 redistribute CNMV documents or derived
                                 full text
paths removed:                   p0/docs/   (34 CNMV PDFs)
                                 p0/docling/ (Docling full-text JSON)
                                 p0/ir/     (document IR JSON)
date / procedure:                git clone --no-local -> git filter-repo
                                 --path p0/docs --path p0/docling
                                 --path p0/ir --invert-paths
audit:                           history-wide scan for PDFs, .work
                                 paths, secrets, emails, local paths,
                                 unexpected large blobs — clean except
                                 the sealed g0/environment-lock.json,
                                 which records the interpreter's local
                                 path (kept; editing a sealed artifact
                                 would break its recorded SHA-256)
```

## IMPORTANT — git SHAs inside frozen artifacts

The `git_sha` / `tree_sha` fields embedded in historical freeze
artifacts (`p0/ui-freeze*.json`, `g0/code-freeze.json`,
`p0/results/p0d/p0d-seal.json`, `p0/results/p0f/scorer-seal.json`, …)
reference commits of the **canonical research history** and will not
resolve in this repository.

**File-level SHA-256 seals remain the authoritative integrity
references.** They were verified against the export after filtering:

- `truth-human-v1` content sha `d1f68653…` — verified
- `gold-human-seal` content sha `99682902…` — verified
- `p0d-seal` per-file JSONL hashes — all verified
- `tools/repro/*` byte-identical to the adapter used during the
  experiments (`PROVENANCE.json`)

## Tags

`g0-final-fail`, `g1-final-fail`, `g2-a-final-fail`, `g2-b-final-fail`,
`p0-final-fail` are preserved and point to the rewritten equivalents of
the canonical commits. Their annotated content is unchanged.

## P0-F scorer audit trail

`p0/scorer_versions/scorer-v1.py` (sealed version), the v1→v3 defect
record (`p0/results/p0f/scorer-v1-to-v2.md` + `.diff`) and the v1 result
set (`p0/results/p0f/v1/`) are preserved unmodified. The evaluation had
scorer defects, they were fixed mechanically with version history kept,
and the FAIL verdict was robust to all corrections (TIME fails under
every scorer version).
