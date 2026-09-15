# Emisiones ES

Capa abierta y auditable de referencia de valores, emisiones, documentación y
términos contractuales para instrumentos emitidos o admitidos en los mercados
españoles.

**Estado**: G1 congelado como FAIL permanente (`g1-final-fail`). Fase
abierta: G2-A — document backend & semantic evidence research. Los
holdouts G1 están consumidos y pasan íntegros a development.

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
| `g0/manifests/` | Muestreo, umbrales y versiones congeladas |

## Lo que NO es

No es un scraper más de la CNMV, ni un wrapper de FIRDS, ni un security
master comercial, ni un "Bloomberg open source". No redistribuye datos de
mercado sujetos a licencia (BME).
