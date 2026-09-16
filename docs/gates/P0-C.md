# P0-C — WARM-UP / USABILITY SMOKE

**Estado:** freeze v1 + ingest + smoke técnico ejecutados; warm-up humano pendiente.
**HEAD:** `f8fe58c` (+ cambios P0-C en commit posterior).

## Pre-flight (ejecutado)

- `git status` limpio en `f8fe58c`.
- Procesos en background: solo `bdns-archive-es` (otro proyecto); nada escribe en este repo.
- 19/19 tests P0-B verdes.

## Errata P0-SAMPLE-v1.1 (detectada en ingest mecánico, antes de cualquier revisión)

La muestra v1 (`93953f0e…`) admitía denominaciones no-deuda en el pool: 9/10
casos MEDIUM eran warrants (`W.CALL …`, `PUT EUR/USD`), no `BONOS/OBLIG.`.
Corregido: pool restringido a denominaciones de deuda instrument-defining,
`MEDIUM == 'BONOS/OBLIG.'` exacto, misma seed `20260916`, selección en orden
HIGH→MEDIUM→LOW (el universo estructurado 2019-2020 es ~91% Bankinter — sin
ese orden el cap de emisor impedía llenar HIGH). Muestra v1.1:
`c8bc3cf71da75e95…` — 30 casos, 15 emisores, máx 30%, todo FAMILY_COLD.
Ninguna revisión humana se había ejecutado; artifacts v1 de casos que no
persisten quedaron descartados.

## Freeze v1

`p0/ui-freeze.json` — `freeze_version=1`, `purpose=PRE_WARMUP`,
git `f8fe58ca57`, tests rc=0. Sellos de app code, manifests,
candidate engine (`src/emissions_es/extraction`), graph engine
(`src/emissions_es/linking`).

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

El warm-up de usabilidad real (los 4 casos con un revisor mirando la UI)
no lo puede ejecutar esta fase automáticamente. Sesión preparada:
`p0/runtime/session_warmup_2f131b62.json` (4 casos, ASSISTED).

```text
python -m p0.app.server --session p0/runtime/session_warmup_2f131b62.json --port 8766
```

Tras el warm-up humano: registrar issues (taxonomía §7), aplicar solo fixes
permitidos (§8), verificar inmutabilidad de candidates (§9), generar
`p0/ui-freeze-final.json` (`--version 2 --purpose P0-D-FINAL
--supersedes p0/ui-freeze.json`), y entonces P0-D.
