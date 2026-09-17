# Emisiones ES

Capa abierta y auditable de referencia de valores, emisiones, documentación y
términos contractuales para instrumentos emitidos o admitidos en los mercados
españoles.

**Estado**: línea de investigación de extracción cerrada
(`g0/g1/g2-a/g2-b` — todos `-final-fail`; veredictos en `docs/gates/`).
La extracción contractual automática general queda **descartada
experimentalmente**. Fase abierta: **P0 — productization / reviewer
workflow** (securities reference-data & document intelligence con
extracción human-in-the-loop basada en evidencia). Ver
[`docs/gates/P0.md`](docs/gates/P0.md).

## Hipótesis de producto

Existe valor diferencial en reconstruir el **grafo documental** de una emisión
(folleto base → suplementos → condiciones finales → correcciones/redepósitos →
admisión) y en extraer **términos contractuales profundos** con provenance a
nivel de campo, que no están disponibles de forma estructurada en FIRDS/ESAP.

El objeto canónico del sistema es el **instrumento financiero**, no el PDF ni
el registro de un venue concreto.

## Principio rector: REUSE FIRST

El código propio se limita a:

1. adaptadores de fuentes específicas (CNMV, venues),
2. *document/security linkage*,
3. extracción de términos contractuales,
4. reconciliación entre fuentes.

Todo lo demás se resuelve con OSS existente. Ver
[`docs/oss-reuse-matrix.md`](docs/oss-reuse-matrix.md).

## Estructura del repositorio

```text
src/emissions_es/   paquete Python: modelo canónico, clasificación,
                    extracción, linking, reconciliación, verificación
p0/                 fase P0 — reviewer app + protocolo de evaluación
  app/              servidor HTTP stdlib + UI de revisión asistida
  manifests/        protocolo, muestra y esquema congelados
  results/          artefactos sellados de evaluación (reviews, gold)
g0/ g1/ g2/         fases de investigación cerradas (manifests, truth,
                    resultados, informes de gate)
tools/              scripts de pipeline (ingest, freeze, scoring)
docs/               arquitectura, contratos, gates preregistrados
tests/              suite pytest (offline, fixtures sintéticas)
```

## Instalación

Requisitos: **CPython 3.13** (el entorno canónico congelado es
Windows/3.13.11; ver `g0/environment-lock.json`).

```powershell
python -m venv .venv            # o: uv venv --python 3.13
uv pip install --python .venv -r requirements-lock.txt   # entorno congelado
```

Sin `uv`, equivalente con pip:

```powershell
.venv\Scripts\python -m pip install -r requirements-lock.txt
```

El lock fue compilado en Windows (`uv pip compile pyproject.toml --extra dev`)
y su SHA-256 está sellado en `g0/code-freeze.json`; no se regenera.

## Tests

```powershell
.venv\Scripts\python -m pytest tests/ -q
```

La suite es offline y usa documentos sintéticos; no requiere el corpus CNMV.
Un test de regresión del frontend usa `node` si está disponible (skip si no).

## Reviewer app (P0)

```powershell
.venv\Scripts\python -m p0.app.server --session p0/runtime/session_<id>.json --port 8765
```

La app solo escucha en loopback (127.0.0.1) y exige Host/Origin same-origin.
Las sesiones se crean con `p0/app/session.py` (`dev_session` para UI sobre
casos de desarrollo G1; `p0_session` desde `p0/manifests/assignments.json`).

## Política de datos

**Este repositorio no distribuye documentos CNMV** ni texto completo derivado
(PDFs, salidas Docling, IR): CNMV no publica una licencia open-data
estándar para ese contenido. Solo se publican hashes, metadatos, evidence pointers y hechos
normalizados (ver `docs/licensing.md`). Los documentos de la muestra P0 se
obtienen de su `document_url` oficial. El ingest mecánico
(`p0/ingest_p0.py`: fetch, Docling, IR, candidates sellados) es
maquinaria del owner — usa el adaptador IR congelado de `.work/g2a/ir/`,
que no se distribuye.

Los artefactos de evaluación congelados (`p0/manifests/`, `p0/results/`,
`g*/manifests/`, `g*/holdout-truth/`) **no se modifican**: su integridad está
sellada por SHA-256 y protegida por tests (`test_freeze_guard`,
`test_g1_freeze_guard`).

## Documentación

| Documento | Contenido |
|---|---|
| `docs/architecture.md` | Arquitectura G0 (tiers deterministas) |
| `docs/source-map.md` | Mapa de fuentes primarias y endpoints |
| `docs/oss-reuse-matrix.md` | Inventario OSS + decisiones de reutilización |
| `docs/licensing.md` | Licencias y riesgos de reutilización de datos |
| `docs/canonical-model.md` | Modelo conceptual mínimo |
| `docs/venue-model.md` | Venues e infraestructuras registradas en CNMV |
| `docs/gates/G0*.md` | Definición de gates, umbrales preregistrados |
| `docs/gates/P0*.md` | Protocolo de evaluación de producto P0 |
| `docs/gates/R0.md` | Gate de publicación: canonical privado → export público sanitizado |
| `g0/manifests/` | Muestreo, umbrales y versiones congeladas |

## Lo que NO es

No es un scraper más de la CNMV, ni un wrapper de FIRDS, ni un security
master comercial, ni un "Bloomberg open source". No redistribuye datos de
mercado sujetos a licencia (BME).

## Licencia

Apache-2.0 (código). Los datos de fuentes primarias conservan sus términos
originales — ver `docs/licensing.md`.
