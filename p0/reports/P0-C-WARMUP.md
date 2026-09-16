# P0-C — Warm-up report

**Verdict: PASS** · freeze final: `p0/ui-freeze-final.json` (git `afc0991f53`)

## Ejecución

4/4 warm-ups humanos completados (A: MANUAL LOW + ASSISTED HIGH;
B: ASSISTED MEDIUM + MANUAL HIGH), todos submitted con 28/28 campos y
10/10 críticos. Closeouts automáticos completos en
`p0/results/warmup/` (`closeouts` en runtime sessions + technical smoke).

## Issues encontrados

| id | categoría | estado |
|---|---|---|
| WU-1 | EVIDENCE_RENDER_BUG (`[object Object]` en valores) | FIXED |
| WU-2 | EVIDENCE_RENDER_BUG (excerpt literal → falso BROKEN_EVIDENCE) | FIXED |
| WU-3 | PRODUCT_LOGIC_REQUEST (misattribution de candidates) | LOGGED_ONLY |

Detalle y trazabilidad en `p0/results/warmup/issues.json`.

## Checks de cierre

```text
4/4 submitted                     OK
0 broken evidence                 OK
0 wrong-document pointers         OK
0 timer/event-log defects         OK
0 blocking UX issues              OK (2 fricciones corregidas)
candidate/graph/sample/assignments/protocol/schema hashes
                                  SIN DRIFT vs freeze v1.2
tests                             20/20 PASS
product-logic changes             0
```

## Próximo paso

P0-D: 60 timed blind reviews (30 casos × 2 modos cruzados), sesiones desde
`assignments.json` + `p0_session()`. No iniciado.
