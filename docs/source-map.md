# Mapa de fuentes primarias — Emisiones ES

Fecha: 2026-09-14. Todo endpoint listado debe re-verificarse en el momento de
construir el adapter; la CNMV se reserva el derecho a cambiar la estructura.

## 1. CNMV — fuente central

### 1.1 Superficie web conocida

| Recurso | URL / endpoint | Tipo | Notas |
|---|---|---|---|
| Folletos de emisión y OPVs | `www.cnmv.es/portal/consultas/busqueda?id=19` | WebForms | Búsqueda por entidad, fechas, últimos días |
| Folletos de admisión | `www.cnmv.es/portal/consultas/busqueda?id=20` | WebForms | Admisiones a cotización |
| Condiciones finales presentadas | `www.cnmv.es/portal/consultas/busqueda?id=35` | WebForms | Punto de entrada del registro de CCFF |
| Condiciones finales por emisor | `www.cnmv.es/portal/consultas/folletos/condiciones-finales?nif={NIF}&page={n}` | Tabla HTML | Devuelve filas con: finalidad (ADMISION/OFERTA), fecha presentación, id `CCFF_{reg}_{seq}`, nº registro oficial, tipo de valor, nominal, **ISIN**, mercado de admisión (AIAF, MARF…) |
| Pasaportes recibidos | `www.cnmv.es/portal/consultas/busqueda?id=…` | WebForms | Folletos UE con pasaporte a España |
| Consulta de códigos ISIN | sección Emisiones/Admisiones | WebForms | Listado ISIN↔emisor |
| Escrituras de anotaciones en cuenta | sección Emisiones/Admisiones | WebForms | Emisiones representadas por anotaciones |
| OPAS | sección Emisiones/Admisiones | WebForms | Ofertas públicas de adquisición |
| Operaciones de registro semanales | `www.cnmv.es` sección consultas | Listado | Registro semanal de operaciones |
| Relación de infraestructuras | `www.cnmv.es/portal/consultas/rectoras/listadosim` | Tabla HTML | Venues: ver `venue-model.md` |
| Servicio de documentos | `www.cnmv.es/webservices/verdocumento/ver?t={guid}` y `?e={token}` | Descarga PDF | Recupera el PDF del registro; `verDoc.axd?t={guid}` es la variante legacy |
| Portal nuevo | `internet.cnmv.es/portal/Consultas/Folletos/FolletosEmisionOPV` | SPA (probable XHR/JSON) | Devuelve tabla con fecha registro, nº registro, emisor, folleto, ISIN, mercado. **Pendiente**: inspección de XHR con devtools para localizar el API JSON detrás |
| Catálogo datos.gob.es | `datos.gob.es/catalogo/ea0042970-folletos-de-emisiones-admisiones-y-opas-registrados-en-la-cnmv` | Metadatos | Las distribuciones apuntan al portal HTML, no a dump CSV real |

### 1.2 Reglas de observación (obligatorias en el adapter)

Cada observación guarda como mínimo:

```text
source, source_record_id, source_url, observed_at, snapshot_hash, retrieved_at
```

- `source_record_id` CNMV no es inmutable: las filas pueden modificarse
  (campo "última modificación" ya visible en CCFF). Tratar como mutable.
- El `Nº de registro oficial` no es clave universal: una emisión puede tener
  varios documentos, y un folleto base puede dar lugar a N condiciones
  finales.

## 2. ESMA — FIRDS / FITRS / ESAP

| Recurso | Endpoint | Tipo |
|---|---|---|
| FIRDS file list | `registers.esma.europa.eu/solr/esma_registers_firds_files/select?…` (API documentada en ESMA65-8-5014) | XML/JSON→ZIP/XML |
| FITRS | `fitrs.esma.europa.eu/fitrs/{DLTNCR|FULECR…}_{date}_*.zip` | ZIP/XML |
| ESAP | portal ESMA, público ~2027-07 | API/portal (futuro upstream) |

Campos FIRDS relevantes (RTS 23, tabla 3 anexo): ISIN, FISN, CFI, LEI emisor,
MIC venue, fechas de solicitud/aprobación/admisión, importe nominal total,
fecha vencimiento, divisa del nominal, nominal por unidad, **tipo fijo**,
índice/benchmark + spread en puntos básicos (flotantes), seniority
(SNDB/MZZD/SBOD/JUND). **No** hay: calendario de call/put, day-count,
frecuencia, reset/fixing, barreras, autocall, fórmulas de amortización,
relaciones documentales.

## 3. GLEIF

API pública `api.gleif.org` (LEI → entidad, dirección, relaciones
padre/hijo). Adapter vía `pygleif` (v2 `GleifClient`).

## 4. Venues españoles (detalle en `venue-model.md`)

| Venue | Tipo | Datos públicos relevantes |
|---|---|---|
| AIAF (Mercado de Renta Fija AIAF) | Mercado regulado | Listado de valores admitidos; referencia en filas CNMV |
| MARF | SMN | Lista pública de emisiones/emisores en bmerf.es |
| BME MTF Equity / BME Growth | SMN | Cotizadas PYME; menos relevante para deuda |
| SENAF | SMN | Deuda pública electrónica |
| Latibex | SMN | Renta variable latam; fuera de foco |
| DOWGATE MTF | SMN | Operado por Archax Markets Europe S.V. (antes KSCM) |
| Portfolio Stock Exchange | SMN | ~31 emisiones listadas (portfolio.exchange); documentación de incorporación por valor |
| CAPI OTF, CIMD OTF, VAMOS OTF, Tradition España OTF | SOC | Negociación organizada deuda/derivados; no admisiones públicas de emisiones |
| SECURITIZE | SNL-TRD | Primer SNL DLT autorizado (2025-11); primera emisión esperada 2026 |

## 5. Otras

- **datos.gob.es**: metadatos de datasets CNMV; las distribuciones suelen
  remitir al portal, no a ficheros descargables — no asumir dump oficial.
- **Registro Mercantil / BORME**: fuera de alcance G0.
- **OpenFIGI**: posible apoyo de mapeo de identificadores (API key, T&C
  propios) — opcional, no núcleo.

## 6. Gaps / verificación pendiente antes de construir adapters

1. Confirmar si `internet.cnmv.es` expone JSON público (devtools XHR).
2. Confirmar si el buscador `id=19/20/35` acepta GET con parámetros o exige
   POST WebForms + ViewState (afecta a diseño del adapter).
3. Confirmar que `verdocumento/ver?t=` acepta tokens estables enlazables
   desde las tablas de CCFF.
4. Confirmar términos de uso de portfolio.exchange.
