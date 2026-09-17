# Emisiones ES

**Research-grade open infrastructure for Spanish securities/document
data** — validated acquisition, identity, document graph and
conservative linkage, plus a complete, hash-sealed experimental record
of approaches that did and did not work.

This is not a ready-to-use contractual-extraction tool and not a
validated reviewer product. It is the audited infrastructure and the
experimental evidence behind those conclusions.

## Results (all gates preregistered, all verdicts sealed)

| Phase | Question | Verdict |
|---|---|---|
| G0 | Can acquisition + deterministic tiers + extraction hit frozen thresholds? | **FAIL** |
| G1 | Improved extraction on a stratified dev set? | **FAIL** |
| G2-A / G2-B | Document graph / docling-IR variants? | **FAIL / FAIL** |
| P0 | Human-in-the-loop reviewer product (manual vs assisted, 30 crossed cases, blinded human gold)? | **FAIL** — assisted was *slower* (median time ratio 1.387, gate ≤ 0.60; only 7/30 cases faster; 95% CI [1.18, 1.75]) and confirmed-value precision vs human truth was 0.43 (gate ≥ 0.99) |

Every gate definition, threshold and dataset was frozen before
evaluation; every result carries SHA-256 artifact seals. The negative
results are the finding: they are preserved, not deleted. See
`docs/gates/` and `p0/reports/P0-F-FINAL-EVALUATION.md`.

### What is demonstrated to work

- Acquisition and identity resolution over CNMV admission records
- The canonical instrument model (`src/emissions_es/`)
- The document-graph and conservative linkage machinery
- The sealed evaluation harness itself: freeze manifests, blinded
  scoring, evidence validation, one-shot scorer with defect versioning
- The reviewer web app (functional; loopback-only, hardened)

### What is experimentally rejected

- General automatic contractual extraction (G0/G1/G2)
- The assisted-review workflow as configured (P0): candidates covered
  only ~26% of human-gold confirmed fields, so assisted review cost more
  time than it saved

## Repository layout

```text
src/emissions_es/   canonical model, classification, extraction,
                    linking, reconciliation, verification
p0/                 P0 phase — reviewer app + frozen evaluation protocol
  app/              stdlib HTTP server + assisted-review UI
  manifests/        frozen protocol, sample, schema
  results/          sealed evaluation artifacts (reviews, gold, scores)
  score_p0.py       one-shot scorer (v1→v3 audit trail preserved)
g0/ g1/ g2/         closed research phases (manifests, results, reports)
tools/repro/        frozen IR adapter (post-evaluation preservation,
                    byte-identical + PROVENANCE.json)
docs/               architecture, contracts, preregistered gates
tests/              pytest suite (offline, synthetic fixtures)
```

## Install

Requires **CPython 3.13** (canonical frozen env: Windows/3.13.11;
see `g0/environment-lock.json`).

```powershell
uv venv .venv --python 3.13
uv pip install --python .venv -r requirements-lock.txt   # frozen env
uv pip install --python .venv -e .                        # package itself
# or, without uv:
python -m venv .venv && .venv\Scripts\python -m pip install -r requirements-lock.txt -e .
```

The lock was compiled on Windows (`uv pip compile pyproject.toml
--extra dev`); its SHA-256 is sealed in `g0/code-freeze.json`.

## Tests

```powershell
.venv\Scripts\python -m pytest tests/ -q
```

Fully offline. Tests that need the (non-distributed) CNMV corpus or
`.work/` artifacts **skip** automatically; the rest use synthetic
fixtures. One frontend regression test uses `node` if present.

## Reviewer app (P0)

```powershell
.venv\Scripts\python -m p0.app.server --session p0/runtime/session_<id>.json --port 8765
```

Loopback-only (127.0.0.1) with same-origin Host/Origin checks. Sessions
are created via `p0/app/session.py`. Document views need the local CNMV
corpus (not distributed — see below) and will 404 without it.

## Data policy

**This repository does not distribute CNMV documents** or derived
full-text (PDFs, Docling output, IR): CNMV publishes no standard
open-data licence for that content. Only hashes, metadata, evidence
pointers and normalized facts are published (`docs/licensing.md`).
P0 sample documents are obtainable from their official `document_url`.
The mechanical ingest (`p0/ingest_p0.py`, sealed) imports the IR adapter
now preserved in `tools/repro/` — redirect its `sys.path` entry from
`.work/g2a/ir` to `tools/repro/` to rerun the pipeline on your own
corpus.

Frozen evaluation artifacts (`p0/manifests/`, `p0/results/`,
`g*/manifests/`) are **never modified**: integrity is SHA-256-sealed and
protected by `test_freeze_guard` / `test_g1_freeze_guard`.

## Publication provenance

This public repository is a history-sanitized export of the private
canonical research repository — see `docs/PUBLICATION_PROVENANCE.md`.
File-level SHA-256 seals inside artifacts remain the authoritative
integrity references; embedded `git_sha`/`tree_sha` fields in historical
freezes refer to the canonical history and may not resolve here.

## Documentation

| Doc | Contents |
|---|---|
| `docs/architecture.md` | G0 architecture (deterministic tiers) |
| `docs/source-map.md` | Primary sources and endpoints |
| `docs/oss-reuse-matrix.md` | OSS inventory + reuse decisions |
| `docs/licensing.md` | Data licences and reuse risks |
| `docs/gates/*.md` | All gate definitions + verdicts |
| `p0/reports/` | P0 evaluation reports |

## What this is not

Not another CNMV scraper, not a FIRDS wrapper, not a commercial security
master, not an "open-source Bloomberg". It does not redistribute
licensed market data (BME).

## Licence

Apache-2.0 (code). Primary-source data retains its original terms — see
`docs/licensing.md`.
