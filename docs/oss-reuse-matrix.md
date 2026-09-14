# G0-A: Matriz de reutilización OSS

Fecha de auditoría: 2026-09-14.

Decisión por pieza: `ADOPT | FORK | WRAP | REFERENCE | CUSTOM | REJECT`.

## Dependencias candidatas del núcleo

| Proyecto | Repo | Versión/estado | Licencia | Mantenimiento | Capacidad | Decisión | Motivo / riesgos |
|---|---|---|---|---|---|---|---|
| pyfirds | `bunburya/pyfirds` | creado 2023-05; sin releases PyPI recientes visibles; actividad baja (0★) | MIT | Bajo/puntual | Descarga FIRDS (ESMA+FCA), `iterparse` incremental XML→dataclasses | **ADOPT (con contingencia FORK)** | Única pieza OSS que ya hace iterparse de FIRDS. Riesgo: deriva del endpoint/formato ESMA y bajo mantenimiento → pinear commit, tests de contrato contra un fichero FIRDS real congelado en snapshot; si falla, FORK |
| esma_data_py | `European-Securities-Markets-Authority/esma_data_py` | 0.0.1, repo oficial ESMA; issues abiertos (DLTECR/FULINS/DLTINS no parsean; PR #7 abierto) | EUPL-1.2 | Activo pero inmaduro | Descubrimiento y descarga de datasets del registro ESMA (`load_mifid_file_list`, `load_latest_files`) | **WRAP** | Usar solo para listar/descargar ficheros (FULINS/DLTINS), detrás de un adaptador propio. EUPL es copyleft → mantener como dependencia opcional aislada; el parsing lo hace pyfirds. Coste de sustitución bajo: la query al endpoint ESMA es trivial |
| Docling | `docling-project/docling` + `docling-core` | ~64k★, muy activo (v2.x) | MIT (código); modelos según sus propias licencias | Muy activo (IBM) | `DoclingDocument`: jerarquía, tablas, `key_value_items`, `ProvenanceItem` (page_no, bbox, charspan) | **ADOPT** | Cubre modelo documental + provenance de layout. No construir modelo documental paralelo. Verificar licencias de modelos concretos usados (p.ej. TableFormer) antes de fijar pipeline |
| gmft | `conjuncts/gmft` | v0.4.x, ~540★, activo | MIT; backend por defecto pypdfium2 (BSD). OJO: `gmft_pymupdf` es repo aparte por AGPL de PyMuPDF | Activo | Detección+formato de tablas PDF (Table Transformer / DITR / histogram) | **WRAP (TIER 2)** | Solo escalado para fallos documentados de TIER 0/1. Prohibido introducir `gmft_pymupdf` (AGPL) |
| Camelot | `camelot-dev/camelot` | ~3.8k★, mantenimiento moderado | MIT | Moderado | Extracción de tablas PDF (lattice/stream) | **WRAP (TIER 2)** | Fallback clásico para tablas con reglas; evaluar vs gmft en ablación, no asumir que ambos son necesarios |
| prov | `trungdong/prov` | v3.1.1, ~135★ | MIT | Bajo pero estable | W3C PROV: PROV-O/JSON/XML, export a graph | **ADOPT (opcional)** | Serialización/interoperabilidad del grafo de provenance. Estados OBSERVED/DERIVED/… se modelan propios; prov solo para export |
| FINOS CDM | `finos/common-domain-model`, paquete `finos-cdm` | CDM 7.0 (2026-07); finos-cdm ≥7.x, Python ≥3.11 | Spec: Community Specification License 1.0; bindings Python: Apache-2.0 | Muy activo | Modelo canónico de productos/instrumentos financieros | **REFERENCE + OPTIONAL DEV DEP** | Sin dependencia runtime dura, sin copiar código del modelo. Produce mapping explícito CNMV→canónico→CDM→FIRDS |
| QuantLib | `lballabio/QuantLib` (+`QuantLib-Python`/SWIG) | Maduro, releases continuos | BSD-3 (modified BSD) | Activo | Schedules, day-count, business-day, cashflows, mecánica de bonos | **REFERENCE / ORACLE (dev)** | Oráculo de validación en tests, no dependencia de producción. No reimplementar day-count ni schedules |
| OpenGamma Strata | `OpenGamma/Strata` | ~950★ | Apache-2.0 | Activo | Mismo dominio que QuantLib (Java) | **REFERENCE** | Segundo oráculo conceptual; Java → sin dependencia runtime |
| pygleif | `ggravlingen/pygleif` | 2026.7.3 | MIT | Activo | Cliente API GLEIF (v2: `GleifClient`) | **ADOPT** | Nota: últimas versiones exigen Python ≥3.13 — fijar floor de Python del proyecto acorde |
| secref-data | `finos/secref-data` | ARCHIVED (2020) | Apache-2.0 | Archivado | Diseño de mapeo de identificadores (ISIN/LEI/FIGI), security master | **REFERENCE** | Solo decisiones históricas de diseño. No es dependencia |

## Infraestructura auxiliar (estándar, sin decisión destacada)

`pydantic` (MIT), `pandas` (BSD-3), `lxml` (BSD), `httpx`/`requests` (BSD/Apache-2.0),
`pypdfium2` (BSD — backend PDF de gmft/docling), `duckdb` (MIT, almacenamiento
local opcional), `pytest` (MIT). Todas transitivas o auxiliares; documentar
versiones fijadas en `g0/manifests`.

## Evaluados y descartados / restringidos

| Proyecto | Licencia | Decisión | Motivo |
|---|---|---|---|
| Marker (`VikParuchuri/marker`) | GPL-3.0 código; pesos con términos adicionales | **REJECT** | Copyleft fuerte + licencia de pesos incompatible con núcleo abierto |
| MinerU (`opendatalab/MinerU`) | Apache-2.0 **modificada** con condiciones extra | **REJECT (core); benchmark OK** | Condiciones adicionales no estándar; reevaluar solo si cambia la licencia |
| rateslib | CC BY-NC-ND 4.0 | **REJECT** | No comercial + no derivadas: incompatible con dataset/código abierto |
| PyMuPDF | AGPL-3.0 / comercial | **REJECT** | AGPL; usar pypdfium2 como backend |
| `shatteringlass/FIRDS-py` | BSD-3 | **REJECT** | Abandonado (2019), enfoque XSLT; superado por pyfirds |
| OpenFIGI (API) | Términos propios de Bloomberg; requiere API key | **REFERENCE (opcional)** | Útil para mapear identificadores en reconciliación manual; no redistribuir mappings sin revisar Términos |
| `marcosagni98/cnmv-xbrl` | MIT | **REFERENCE** | Parser XBRL de informes de IIC/SICAV CNMV — dominio distinto (fondos), pero patrón útil de adapter CNMV |
| Scrapers CNMV varios (`Alvaru89/final_project_CNMV`, `msc3po/Sicav_Scraper`, `afernandez119/cnmv_data`) | varias/none | **REJECT** | Cubren fondos/SICAV, no emisiones; sin modelo documental ni provenance |

## Capacidades sin cobertura OSS → CUSTOM (núcleo del proyecto)

| Capacidad | Evidencia de vacío |
|---|---|
| Adapter CNMV (folletos, condiciones finales, admisiones, ISIN, infraestructuras) | Solo existen scrapers de IIC/SICAV; nada para emisiones/OPV/admisiones con provenance |
| Document graph de emisión (base↔suplemento↔CCFF↔corrección↔redepósito↔admisión) | No existe OSS que modele el linaje documental del régimen de folletos UE 2017/1129 en España |
| Extracción de términos contractuales (call/put, reset, barreras, autocall, day-count) | FIRDS/RTS 23 no reporta estos campos; no hay extractor OSS ES/UE |
| Reconciliación CNMV↔FIRDS↔GLEIF↔venues con estados AGREE/CONFLICT/… | Específico del proyecto |

**Veredicto G0-A**: no se ha encontrado ningún OSS que resuelva el núcleo
(document graph + términos contractuales con provenance para mercado español).
Las piezas existentes cubren las capas genéricas tal como exige REUSE FIRST.
