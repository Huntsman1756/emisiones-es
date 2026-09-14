# Licencias y reutilización de fuentes de datos

Fecha de auditoría: 2026-09-14. Esto no es asesoramiento legal; es el registro
de riesgos de reutilización que condiciona el diseño del G0.

## Software (resumen)

| Pieza | Licencia | Impacto |
|---|---|---|
| pyfirds, docling, gmft, camelot, prov, pygleif, cnmv-xbrl | MIT | Sin restricción material |
| esma_data_py | **EUPL-1.2** | Copyleft europeo. Mantener como dependencia opcional aislada (solo discovery/download); no copiar código al núcleo |
| finos-cdm (bindings) | Apache-2.0 / spec CSL-1.0 | OK como dev-dependency; la *spec* es CSL → no copiar definiciones del modelo |
| QuantLib | BSD-3 | OK como oráculo en tests |
| Strata, secref-data | Apache-2.0 | OK como referencia |
| Marker | GPL-3.0 + pesos restringidos | REJECT |
| MinerU | Apache-2.0 modificada | REJECT del núcleo |
| rateslib | CC BY-NC-ND 4.0 | REJECT |
| PyMuPDF | AGPL-3.0 | REJECT (incl. `gmft_pymupdf`) |

## Datos / fuentes primarias

### CNMV (cnmv.es, sede.cnmv.gob.es)

- La [nota legal](https://www.cnmv.es/portal/utilidades/notalegal.aspx)
  afirma copyright sobre "textos, fotos y elementos gráficos" del sitio y su
  presentación, y exime de responsabilidad. No publica una licencia de
  reutilización abierta para el contenido de la web.
- **Matización importante**: los *folletos, condiciones finales y suplementos*
  son documentos de los emisores registrados por obligación legal (Reglamento
  UE 2017/1129), no contenido editorial de la CNMV. La difusión pública es un
  deber legal; el dataset resultante son **hechos extraídos** (términos,
  fechas, importes), no republicación del texto.
- `datos.gob.es` cataloga datasets CNMV (p.ej. "Folletos de emisiones,
  admisiones y OPAS") con condiciones de uso que remiten a la nota legal.
- **Decisión de diseño**: el dataset publica *datos estructurados + hashes +
  URLs fuente*, no los PDFs. Los snapshots locales se conservan para
  auditoría pero no se redistribuyen por defecto. Riesgo residual: MEDIO,
  mitigable publicando solo hechos + metadatos de provenance.

### ESMA — FIRDS / FITRS / ESAP

- Datos del registro ESMA publicados como open data de la UE (dataset
  "Financial Instruments Reference Data System" en data.europa.eu).
  Reutilización libre. Sin restricción material.
- FIRDS cubre solo los campos de RTS 23 (ver `docs/gates/G0-OSS-DELTA.md`).

### GLEIF

- API pública y abierta; los datos LEI se distribuyen bajo términos de GLEIF
  (uso libre con atribución). Bajo riesgo; respetar rate limits.

### BME (bolsasymercados.es, AIAF, MARF, MEFF)

- Los datos de mercado de BME están sujetos a licencias comerciales de
  *market data*. **Decisión**: BME es REFERENCE/VALIDATION ONLY en G0.
  No se redistribuyen precios, cupones corridos ni listados BME; solo se usan
  campos factuales mínimos (p.ej. "admitido en AIAF") cuando el propio
  documento/la CNMV ya los publica.

### Portfolio Stock Exchange (portfolio.exchange)

- SMN operado por European Digital Securities Exchange, S.V., S.A.
  (LEI `959800UP9ANDBHTKJ408`, registro CNMV nº 314). Publica reglamento,
  lista de valores admitidos (~31 emisiones listadas, mayoría SOCIMIs de
  renta variable; la renta fija existe pero es minoritaria). Términos de
  reutilización del sitio por verificar → tratar como BME: hechos factuales
  mínimos + URL, sin republicación de contenido.

### SECURITIZE (SNL TRD)

- Autorizado por CNMV (acuerdo de consejo publicado 2025-11-26) bajo el
  régimen piloto DLTR (Reglamento UE 2022/858). Operado por Securitize Europe
  Brokerage and Markets, S.V., S.A.; primera emisión anunciada para 2026
  sobre Avalanche. Material público de emisiones: probablemente escaso aún →
  el caso DLT del corpus puede tener que ser *design-case* sobre el
  reglamento/autorización, no sobre una emisión real.

### ESAP (estado)

- Recolección fase 1 iniciada 2026-07-10 (OAMs + NCAs → ESMA); portal público
  previsto para 2027-07. Fase 1 incluye Prospectus Regulation → **ESAP será
  upstream futuro**, no elimina backfill histórico ni términos contractuales
  ni reconciliación.

## Riesgos de reutilización (ranking)

| # | Riesgo | Severidad | Mitigación |
|---|---|---|---|
| 1 | Reutilización de contenido CNMV sin licencia abierta explícita | MEDIO | Publicar hechos extraídos, no PDFs; atribución; logs de origen |
| 2 | Datos de mercado BME con licencia comercial | ALTO si se redistribuyen | REFERENCE/VALIDATION ONLY; sin precios ni listados completos |
| 3 | EUPL de esma_data_py contaminando distribución | BAJO | Dependencia opcional aislada; alternativa CUSTOM trivial |
| 4 | Dependencia AGPL por transitividad (gmft_pymupdf) | BAJO | Prohibido en manifiesto; CI de licencias |
| 5 | Cambio de endpoints CNMV sin aviso (la nota legal lo reserva) | MEDIO | Snapshots + hashes; adapters aislados; tests de contrato |
