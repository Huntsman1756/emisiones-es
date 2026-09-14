# G0-B — LINKAGE golden set

## Definición

300 decisiones manuales de linkage documental. Cada decisión:

```text
source_document_id | candidate_target (document/security/programme | NONE)
label              EXACT_LINK | NO_LINK | AMBIGUOUS
target_id          (si EXACT_LINK)
evidence           campos/span que justifican
annotator, notes
```

## Estratificación preregistrada (suma = 300)

| Estrato | n | Ejemplo |
|---|---|---|
| final terms → programme/base prospectus | 80 | CCFF → folleto base correcto |
| supplement → prospectus | 40 | suplemento nºk → folleto base |
| correction → document corrected | 30 | rectificación → doc original |
| redeposit → previous version | 30 | redepósito → versión previa |
| admission → security/ISIN | 30 | admisión → ISIN concreto |
| hard neg: mismo emisor, programa equivocado | 15 | Santander EMTN vs covered |
| hard neg: mismo ISIN, rol distinto | 10 | misma ISIN en admisión vs CCFF |
| hard neg: título similar, emisor distinto | 15 | programas homónimos |
| no-link / evidencia insuficiente | 25 | doc huérfano |
| multi-venue | 15 | AIAF+MARF, dual-listing, Portfolio |
| AMBIGUOUS de verdad (etiquetado) | 10 | evidencia contradictoria real |
| **Total** | **300** | |

## Métricas preregistradas

```text
exact-target accuracy   >= 98%
precision               >= 99%
recall                  >= 95%
false positive links    = 0
forced links AMBIGUOUS  = 0
silent forced linkage   = 0
```

Sin movimiento de umbrales tras medir. `AMBIGUOUS` en golden + `AMBIGUOUS`
en predicción cuenta como acierto de abstención, no como link.
