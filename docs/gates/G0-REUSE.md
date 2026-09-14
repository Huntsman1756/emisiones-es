# G0-A — REUSE / LICENSING / ARCHITECTURE (informe de discovery)

Fecha: 2026-09-14. Estado: **PASS documental** (todas las capacidades tienen
decisión; ver `../oss-reuse-matrix.md`). Sujeto a re-validación al fijar
versiones en `g0/manifests/g0-manifest.json`.

## Hallazgos que modulan el diseño

1. **pyfirds es la única pieza que hace `iterparse` de FIRDS**, pero con
   mantenimiento bajo → ADOPT con plan FORK y tests de contrato contra un
   fichero FIRDS congelado.
2. **esma_data_py es EUPL-1.2** y tiene parsers incompletos para varios tipos
   de dataset → WRAP solo para listar ficheros; nunca copiar su código.
3. **Docling provee provenance de layout nativo** (page/bbox/charspan) → no
   construir modelo documental paralelo; `ProvenanceItem` es la base de la
   evidencia de campo.
4. **gmft tiene una trampa AGPL**: `gmft_pymupdf` queda prohibido; solo el
   núcleo MIT con pypdfium2.
5. **finos-cdm**: spec CSL-1.0 → REFERENCE + mapping explícito, no copia de
   modelo, no dependencia runtime dura.
6. **No existe OSS** que haga document-graph ni extracción de términos
   contractuales para el régimen de folletos UE en España → el núcleo CUSTOM
   está justificado.
7. **SECURITIZE ya está autorizado** (2025-11-26, SNL-TRD UE 2022/858) → el
   modelo debe soportar `SettlementArrangement` DLT desde el día 1.
8. **Portfolio Stock Exchange existe y publica** reglamento + listado de
   valores (operador European Digital Securities Exchange, LEI
   959800UP9ANDBHTKJ408) → entra en corpus G0.

## Riesgo que vigilar en G0-B/C

- La tabla CNMV de condiciones finales ya expone ISIN + mercado + tipo de
  valor de forma estructurada → el linkage CCFF→programa puede ser parcialmente
  trivial para AIAF; los hard-negatives del golden set deben centrarse en
  casos donde esa tabla no basta (programas multi-vehículo, pasaportes,
  redepósitos, docs sin ISIN en la fila).
