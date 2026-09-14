# Arquitectura G0 (boceto, sujeto a evidencia de ablación)

Principio: *deterministic-first*. Ninguna capa sobrevive si la ablación G0-D
no demuestra utilidad marginal.

## Pipeline factual de extracción

```text
TIER 0  Docling → DoclingDocument
        (textos, jerarquía, key_value_items, tablas, prov: page/bbox/charspan)
        → extractores deterministas por campo (regex/tablas/plantillas)

TIER 1  Docling + TableFormer            (solo si TIER 0 no resuelve estructura)

TIER 2  gmft / camelot                   (solo para fallos documentados)
```

Sin LLM en la ruta factual. Cualquier experimento con modelos queda fuera de
la producción de hechos y requiere evidencia determinista para promoverse.

## Módulos propios (src/emissions_es/)

```text
sources/         adapters CNMV (folletos, CCFF, admisiones, ISIN,
                 infraestructuras), FIRDS (vía pyfirds/esma_data_py),
                 GLEIF (pygleif), venues (Portfolio, MARF…)
linking/         construcción del document graph + golden-set de linkage
extraction/      extractores deterministas por campo con dominio declarado
reconciliation/  cruce multi-fuente con estados AGREE/CONFLICT/SOURCE_ONLY/…
provenance/      TermObservation/SourceObservation, snapshots, hashes,
                 export W3C PROV (opcional, prov)
```

## Almacenamiento

- Snapshots de documentos: `g0/snapshots/` (no redistribuidos).
- Observaciones y provenance: ficheros JSONL + `snapshot_hash` por artefacto.
- DuckDB opcional para consulta; sin servidor.

## Medición de la ablación (G0-D)

Por tier: `documents_escalated`, `pages_escalated`, `fields_recovered`,
`precision_delta`, `recall_delta`, `runtime`, `CPU`, `peak_RAM`.
Umbrales y dominio de cada extractor preregistrados en
`g0/manifests/g0-manifest.json`.
