# G0-B — Acquisition & Holdout Freeze

**Veredicto: PASS** (ver `g0/reports/G0-B-ACQUISITION-REPORT.md` para evidencia)

## Criterios del gate

| Criterio | Estado | Evidencia |
|---|---|---|
| CNMV core surfaces reproducibly retrievable | ✅ | Folletos emisión/OPV, admisión, CCFF, detalle NUMFOL, servicio de documentos y registro de infraestructuras: HTTP 200 por GET paginado, sin sesión obligatoria. `acquisition-results.json` |
| Document URLs resolubles para el corpus | ✅ | 41/41 PDFs del corpus descargados y verificados (`%PDF-` magic, sha256 registrado) |
| Identidad de fuente suficientemente estable para snapshot | ✅ | `source_record_key` + `raw_sha256` + `normalized_row_sha256`; tokens documentales opacos tratados como URL+hash |
| Mutaciones representables sin overwrite | ✅ | `tools/reobserve.py` + `reobservation-results.json`: UNCHANGED/UPDATED_METADATA/UPDATED/DISAPPEARED/NEW |
| linkage scout != linkage holdout | ✅ | 56 scout / 300 holdout; 0 solapamiento de decisiones (verificado programáticamente) |
| extraction scout != extraction holdout | ✅ | 11 scout / 30 holdout; pools disjuntos por registro inspeccionado |
| 300 linkage holdout congelados | ✅ | `linkage-holdout.json`, n=300, 11 estratos, manifest_sha256 `e0f711bf…` |
| 30 extraction holdout congelados | ✅ | `extraction-holdout.json`, n=30, todos con PDF+sha256 |
| Labels de evaluación no han influido implementación | ✅ | No hay linker/extractores implementados; labels por construcción estructural preregistrados |

## Desviaciones preregistradas

1. **Portfolio sin deuda listada**: 31 valores observados, todos
   SOCIMI/equity. El rulebook soporta bonos y la API de documentos
   funciona (con `Referer`), pero no existe caso de deuda real que
   congelar. `Portfolio debt cases found: 0`. No es FAIL: la fuente es
   accesible y el mecanismo documental está probado con un doc equity.
2. **Securitize/DLT**: `DLT_CASE=NOT_AVAILABLE` con evidencia de búsqueda
   (autorizada 2025-11-26, sin emisión pública documentable).
3. **Estrato "redeposit → previous version"** reinterpretado como
   `S4_programme_succession`: no se observan redepósitos como filas
   separadas en la superficie CNMV (mismo registro = misma fecha); el
   linaje de versiones solo se detecta por reobservación. S4 usa la
   sucesión anual de programas del mismo emisor (arista REPLACES).
4. **`consulta_isin` y `CNMVInforma` devuelven 403**: familias
   auxiliares no requeridas para el corpus; documentadas como BLOCKED.
5. **CCFF cobertura temporal corta**: el registro solo muestra ~150
   filas desde 2023; suficiente para el holdout pero limita backfill
   histórico por esa superficie.
6. **2 casos de admisión scout/holdout sin doc_url directo**: la fila
   enlaza al detalle NUMFOL; el token documental se resuelve allí.
   `ADM_143237` sustituido por `ADM_143231` en scout por ese motivo.

## Sustituciones de corpus

Ningún documento preregistrado del holdout resultó inaccesible: 30/30
descargados. No hubo sustituciones en el holdout. En scout se sustituyó
`ADM_143237` → `ADM_143231` (mismo estrato, fila con enlace documental
directo) y `FOL_11424.1` → `FOL_11425.1` (11424 no aparece en las
páginas adquiridas; misma regla de muestreo scout).
