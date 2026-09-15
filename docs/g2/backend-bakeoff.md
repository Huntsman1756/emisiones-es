# G2-A — Backend bake-off protocol

Pregunta: ¿qué backend produce una IR en la que un claim financiero tipado
puede verificarse estructuralmente? No es una competición de OCR.

## Candidatos

| backend | rol |
|---|---|
| Docling 2.126.0 | baseline congelado (misma config que G1-C) |
| PaddleOCR PP-StructureV3 | challenger A |
| deepdoctection (modo Windows, sin Detectron2) | challenger B |
| LayoutParser | REFERENCE_ONLY (release 2022) |

Entornos aislados bajo `.work/g2a/`; versiones, modelos, licencias y
footprint en `g2/research/backend-environments.json`.

## Etapas

```text
Stage 0  smoke      3 docs: plain / table-heavy / structured-cold
                    objetivo: instala, procesa, coordenadas estables,
                    adapter IR funciona. No se miden calidades.

Stage 1  diagnostic ~20 docs: 10 COLD_ISSUER + 10 SEEN_ISSUER
                    variedad: plain, FRN, structured, securities note,
                    final terms, base prospectus
                    métricas de relaciones estructurales exhaustivas

Stage 2  full dev   hasta 97 docs extraction + G1 development relevante
                    solo para backends viables tras Stage 1
```

Stop rule por backend (en Stage 1): coordenadas no fiables, relaciones
estructurales materialmente peores, licencia bloqueante, o coste
desproporcionado → abandonar. No completar 97 por inercia.

## Métricas (a nivel claim, no a nivel OCR)

```text
ANCHOR_FOUND
VALUE_FOUND
ANCHOR_VALUE_RELATION_CORRECT
SECTION_SCOPE_CORRECT
TABLE_CELL_ASSOCIATION_CORRECT
PAGE_PROVENANCE_CORRECT

CLAIM_SUPPORTED_CORRECTLY
CLAIM_REJECTED_CORRECTLY
FALSE_SUPPORTED_CLAIM          # crítico
```

## Selección

No por promedio global. Criterios: semantic-support accuracy, cold-issuer
recall, table relation quality, geometry/provenance, runtime/RAM,
licencia, complejidad de integración. Resultados posibles:
`KEEP_DOCLING | REPLACE_WITH_PADDLE | REPLACE_WITH_DEEPDOCTECTION |
HYBRID | NO_BACKEND_IMPROVES`. HYBRID solo con complementariedad
demostrada; no ensemble preventivo.

## Comparación contra G1

Los errores G1 son truth de desarrollo. Reanálisis de los 101 invented:
para cada claim → `FIXED_TO_REJECT | FIXED_TO_REVIEW |
STILL_FALSE_SUPPORTED | LOST_CORRECT_CLAIM | UNCHANGED_CORRECT`.

Hard objective: `STILL_FALSE_SUPPORTED = 0`.

COLD_ISSUER primario: recall de `coupon_rate / day_count / call_put /
reset_fixing / observation / structured payoff` condicionado a
`false_supported = 0`. No se compra recall con invenciones.

## Kill criterion

G2-A FAIL si, tras el mejor backend + verificador tipado:

- `false-supported claims > 0` de forma no trivial/recurrente, o
- COLD_ISSUER deep-term recall no mejora materialmente sin reglas
  específicas de emisor/plantilla, o
- la única vía de mejora requiere parsers por emisor / layouts
  hard-codeados / reglas manuales a escala.

## Success criterion

Continuar a preregistro G2 solo si: `unsupported/invented = 0` en
development evaluado, mejora material de recall en COLD_ISSUER, y la
mejora proviene de relaciones estructurales/semánticas — no de memorizar
layouts nuevos.
