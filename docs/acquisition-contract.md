# Contrato de adquisición — Emisiones ES (G0-B)

Define cómo se adquiere y versiona evidencia primaria antes de cualquier
linker o extractor. Aplica a todas las fuentes; los detalles por familia
están en `g0/manifests/source-acquisition.json` y los resultados del
sondeo en `g0/results/acquisition-results.json`.

## 1. Regla de adquisición

HTTP directo primero. Las superficies CNMV son ASP.NET WebForms: el POST
del formulario (`busqueda?id=…`) responde con redirección a una URL GET
paginable (`…?fechaDesde=…&fechaHasta=…&page=N`) que es reproducible sin
ViewState ni sesión. **No se usa Selenium ni automatización de navegador**
mientras el GET paginado devuelva las filas completas.

XHR/API interna solo se justifica si aporta ventaja demostrable sobre HTML
(completitud, estabilidad, paginación, identificadores, coste). El portal
`internet.cnmv.es` se inspeccionó y no expone API pública de registro: la
decisión congelada es HTML-first (registrado en `source-acquisition.json`).

Portfolio Stock Exchange: las fichas de instrumento embeben metadatos de
documentos; el endpoint `api.portfolio.exchange/poex/document/{id}`
responde 403 sin `Referer` y 200 `application/pdf` con
`Referer: https://portfolio.exchange/`. La adquisición Portfolio incluye
siempre ese header.

## 2. Observación mínima

Toda adquisición produce un registro con:

```text
source, source_family, source_record_key, canonical_url,
retrieved_at, observed_at (si la fuente lo expone),
http_status, content_type,
raw_sha256, normalized_row_sha256,
document_url, document_sha256 (si existe)
```

Auxiliares (nunca identidad): `ETag`, `Last-Modified`, `Content-Length`,
`redirect_chain`.

`normalized_row_sha256` se calcula sobre las celdas `<td>` normalizadas
(espacios colapsados), ignorando ViewState, banners y markup variable. Es
lo que distingue `UPDATED` (cambió una fila) de `UPDATED_METADATA` (solo
cambió el envoltorio HTML). Implementación de referencia:
`tools/reobserve.py`.

## 3. Versionado

Nunca se sobrescribe una observación. Cada nueva captura es una versión
nueva y la comparación produce:

```text
UNCHANGED          raw_sha256 idéntico
UPDATED_METADATA   raw distinto, normalized_row_sha256 idéntico
UPDATED            normalized_row_sha256 distinto (cambió contenido de fila)
DISAPPEARED        la observación previa ya no es recuperable (≠200)
NEW                registro sin observación previa
```

Demostrado en `g0/results/reobservation-results.json`: 3 pares reales
UNCHANGED, 1 par real UPDATED_METADATA (detalle de folleto entre
capturas: ViewState difiere, filas idénticas), y fixtures para
UPDATED/DISAPPEARED/NEW.

## 4. Identidad CNMV (provisional, no universal)

```text
source_record_key                id de fila observable
  CCFF_{registro}_{seq}          condiciones finales  (CCFF_11400_043)
  FOL_{registro}[.k|-k]          folletos emisión/OPV (FOL_11424.1, FOL_11316-2)
  ADM_{registro 143xxx}          folletos de admisión
  PSE_{issuer}_{docid}           documentos Portfolio
source_document_key              token verdocumento opaco / URL documental
programme_or_prospectus_reference  registro oficial (parte entera)
isin                             por fila; 0..N por registro
observed_version                 presentación + última modificación (CCFF)
                                 fecha_registro + sufijo (folletos)
```

Invariantes observados (verificados en `CCFF_11400_043/044/045`,
`CCFF_11425_001` y el pool completo):

- El **nº de registro oficial NO es id de fila ni de documento**: un
  mismo registro (p.ej. 11400 Santander, 11434 FTA) agrupa N condiciones
  finales, N ISINs y N fechas de presentación/modificación.
- Sufijo `.k` = suplemento k del folleto base; `-k` = modificación k.
  Observado consistentemente; se trata como regla provisional, no
  universal.
- Esquemas de registro heterogéneos: `11xxx` (programas/emisiones),
  `2026xxxxx` (FTA/series), `143xxx` (admisión).
- El token `verdocumento/ver?e=` es opaco y no reversible a id semántico:
  la identidad documental es `URL + sha256 del PDF`.
- Caso edge real: `NUMFOL=11425` solo muestra el suplemento — el folleto
  base no es visible en la superficie de detalle. Se conserva como caso
  `AMBIGUOUS` en el holdout (S11).

## 5. Almacenamiento

- `g0/snapshots/` y `.work/` contienen PDFs/HTML crudo: **gitignored**
  (licencia CNMV, tamaño). Los manifests referencian `url + sha256 +
  retrieved_at + local_evidence`, suficiente para re-verificar.
- `g0/manifests/*.json` y `g0/results/*.json` sí se commitean.

## 6. Lo que NO hace este contrato

No implementa linker, extractores contractuales, ni crawl histórico.
La normalización es solo de adquisición (celdas HTML → fila); no
interpreta términos financieros.
