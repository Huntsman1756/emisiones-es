# Estratificación del golden set G0-B (preregistro)

300 decisiones manuales. Regla: cada decisión evalúa **una** relación
candidata origen→target (incluido target = NONE).

| Estrato | n | Qué se decide | Fuente de casos |
|---|---|---|---|
| S1 final_terms→programme | 80 | CCFF enlaza al folleto base/programa correcto | Tabla CCFF CNMV por emisor |
| S2 supplement→prospectus | 40 | suplemento pertenece a folleto base X | Registro folletos CNMV |
| S3 correction→document | 30 | rectificación corrige doc concreto | Redepósitos/erratas CNMV |
| S4 redeposit→prev_version | 30 | redepósito sustituye versión previa | Mismo nº registro, fecha modificación |
| S5 admission→security | 30 | admisión se refiere a ISIN concreto | Folletos admisión + tabla ISIN |
| S6 same issuer / wrong programme | 15 | hard negative | Emisores con ≥2 programas activos |
| S7 same ISIN / different role | 10 | hard negative | ISIN citado en admisión vs CCFF vs folleto |
| S8 similar title / different issuer | 15 | hard negative | Programas homónimos, SPVs similares |
| S9 no-link / insufficient evidence | 25 | doc sin target resoluble | Docs huérfanos, pasaportes |
| S10 multi-venue | 15 | enlaces correctos con >1 venue | AIAF+MARF, dual listing, Portfolio |
| S11 ambiguous ground truth | 10 | etiquetado AMBIGUOUS de origen | Evidencia contradictoria real |
| **Total** | **300** | | |

## Formato de registro

```text
decision_id, source_document_id, candidate_target_id|NONE,
label(EXACT_LINK|NO_LINK|AMBIGUOUS), stratum, evidence_fields,
annotator, date, notes
```

## Reglas

- El golden set se construye **antes** de implementar el linker.
- `AMBIGUOUS` nunca se resuelve a mano para "ayudar" al sistema.
- Métricas en `docs/gates/G0-LINKAGE.md` (congeladas en `g0-manifest.json`).
