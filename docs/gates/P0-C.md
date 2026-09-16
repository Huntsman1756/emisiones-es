# P0-C — WARM-UP / USABILITY SMOKE

**Estado:** **PASS** — 4/4 warm-ups humanos completados, fixes permitidos aplicados, `ui-freeze-final.json` emitido (`afc0991f53`, tests rc=0). Listo para P0-D.

## Resultado warm-up humano (4/4 submitted)

```text
REVIEWER_A  ADM_120967 MANUAL    516s · 29 decisions · 17 manual adds
            ADM_123650 ASSISTED  319s · 32 decisions · 9 manual adds
REVIEWER_B  ADM_118245 ASSISTED  175s · 30 decisions · 10 manual adds
            ADM_121548 MANUAL    228s · 28 decisions · 16 manual adds
```

Todos: 28/28 campos, 10/10 críticos resueltos, 0 broken evidence,
0 wrong-document, 0 UI errors, event log íntegro (orden + lifecycle,
sin duplicados). Pause/Resume, atajos j/k/c/r/x/e, grafo y saltos de
evidencia ejercitados en las 4 sesiones.

## Issues (`p0/results/warmup/issues.json`)

- **WU-1** EVIDENCE_RENDER_BUG: `[object Object]` en valores dict/list → FIXED.
- **WU-2** EVIDENCE_RENDER_BUG: excerpts literales → BROKEN_EVIDENCE falso positivo; comparación normalizada → FIXED.
- **WU-3** PRODUCT_LOGIC_REQUEST: candidate misattribution
  (coupon_rate↔participación, protection_barrier↔barrera cupón) →
  LOGGED_ONLY. Confirmación empírica del hallazgo G2-B.

Inmutabilidad post-fixes: sample/assignments/protocol/schema/candidate-seal/
engines — 0 drift vs freeze v1.2. Solo cambiaron `app.js` y `evidence.py`
(fixes permitidos §8).

## Enmienda formal de muestra (P0-SAMPLE-v1.1)

`p0/manifests/sample-errata-v1.1.json` — enmienda formal:

```text
P0-SAMPLE-v1    sha 93953f0e…  commit cb81b6f (preservado en git)
P0-SAMPLE-v1.1  sha c8bc3cf7…  motivo: bug estratificación MEDIUM
                20 casos sustituidos, 10 conservados
                re-verificado: overlap G0/G1/G2 = 0 · 30×FAMILY_COLD
                15 emisores · max 30% · 30/30 PDFs válidos
```

`assignments.json` regenerado contra v1.1 (mismo seed) — incluye warm-up
cruzado: cada reviewer hace 1×MANUAL + 1×ASSISTED, nunca el mismo caso en
ambos modos. A: LOW MANUAL + HIGH ASSISTED · B: MEDIUM ASSISTED + HIGH MANUAL.

## Freeze

`p0/ui-freeze-prewarmup-v1.2.json` — `freeze_version=1.2`,
`purpose=PRE_WARMUP`, supersedes v1.1 → v1, tests rc=0. Sellos: app,
manifests, sample-v1.1, assignments, candidate-seal, candidate engine,
graph engine. v1.2 añade instrumentación preregistrada de close-out
(`closeouts.jsonl` + `UI_ERROR` + reviewer_notes UX-only) — sin tocar
lógica de producto.
(`p0/ui-freeze.json` v1 queda obsoleto — fue emitido sobre sample v1.)

Nota de audit trail sobre `git_sha=3cd3e7b` en el freeze v1.2: ese commit
contiene el último cambio funcional de `p0/app/` (instrumentación de
close-out). El commit posterior `035f75f` solo añade el propio artefacto
de freeze + este documento — `git diff 3cd3e7b..035f75f` toca únicamente
`docs/gates/P0-C.md` y `p0/ui-freeze-prewarmup-v1.2.json`. Todos los
hashes sellados en el freeze se verificaron idénticos al estado en HEAD
(`035f75f`). El freeze representa correctamente la aplicación ejecutable.

## Pre-flight (ejecutado)

- `git status` limpio en `f8fe58c`.
- Procesos en background: solo `bdns-archive-es` (otro proyecto); nada escribe en este repo.
- 19/19 tests P0-B verdes.

## Ingest mecánico (post-freeze, lógica congelada)

`p0/ingest_p0.py` sobre los 34 casos (30 holdout + 4 warm-up):
fetch PDF → Docling 2.126 → IR (adapter G2-A) → classify → extract → seal.

Resultado: 34/34 sellados, 354 candidates, clasificados `SECURITIES_NOTE`.
Hashes por caso en `p0/results/candidate-seal.json`.
Validación mecánica de evidencia: **571/571 pointers OK, 0 wrong-document**.
Grafo P0: todos `INCOMPLETE` (admisiones standalone sin familia en corpus) —
estado válido del producto; el ahorro deberá venir de candidates+evidencia.

## Smoke técnico automatizado (no sustituye warm-up humano)

4/4 warm-up cases vía API: CASE_OPENED → EVIDENCE_JUMP + render PNG →
CONFIRM candidate (evidencia auto-adjunta) → REJECT → pausa/reanuda →
manual discovery con pointer → CASE_SUBMITTED → seal con active_seconds
y unresolved_critical. Event log: orden temporal correcto, sin duplicados.
Artefactos en `p0/results/warmup/*-technical-smoke.jsonl`.

## Pendiente (requiere humano)

Warm-up real con revisores — sesiones preparadas:

```text
REVIEWER_A: p0/runtime/session_warmup_eec924b2.json
            (ADM_120967 MANUAL · ADM_123650 ASSISTED)
REVIEWER_B: p0/runtime/session_warmup_0a1eb983.json
            (ADM_118245 ASSISTED · ADM_121548 MANUAL)

python -m p0.app.server --session <session.json> --port 8766
```

P0-C no se cierra hasta que **ambos** reviewers hayan hecho sus warm-ups:
si solo hay uno disponible, hace los suyos pero P0-C queda abierto y no se
emite `ui-freeze-final` hasta que el segundo complete los suyos.

Tras el warm-up humano: registrar issues (taxonomía §7), aplicar solo fixes
permitidos (§8), verificar inmutabilidad de candidates/graph/schema (§9),
generar `p0/ui-freeze-final.json` (`--version 2 --purpose P0-D-FINAL
--supersedes p0/ui-freeze-prewarmup-v1.1.json`), y entonces P0-D.
