# Contribuir a Emisiones ES

## Entorno de desarrollo

```powershell
python -m venv .venv            # o: uv venv --python 3.13
uv pip install --python .venv -r requirements-lock.txt
uv pip install --python .venv -e .
.venv\Scripts\python -m pytest tests/ -q
```

CPython 3.13 es el único intérprete soportado (entorno canónico congelado).

## Reglas de oro

1. **No tocar artefactos sellados.** `p0/manifests/`, `p0/results/`,
   `g*/manifests/`, `g*/holdout-truth/`, `requirements-lock.txt` y
   `g0/environment-lock.json` tienen integridad SHA-256 registrada. Los
   tests `test_freeze_guard` / `test_g1_freeze_guard` fallan si cambian.
   Las correcciones a datos congelados se hacen por **errata versionada**
   (nuevo archivo + registro), nunca por edición in-place.
2. **No commitear documentos fuente.** PDFs CNMV, salidas Docling y IR de
   texto completo viven solo en local (`.work/`, `p0/docs/`, `p0/docling/`,
   `p0/ir/`, snapshots `g*/`). Ver `docs/licensing.md`.
3. **REUSE FIRST.** Antes de escribir código propio, comprobar
   `docs/oss-reuse-matrix.md`: el código propio se limita a adaptadores de
   fuente, linkage, extracción y reconciliación.
4. **CANDIDATE != CONFIRMED.** Ningún valor automático se promociona a
   dato canónico sin decisión humana con evidencia válida.

## Cambios

- Tests: toda corrección o funcionalidad nueva debe venir con tests en
  `tests/` (pytest, offline, fixtures sintéticas — sin corpus real).
- Estilo: código en inglés, documentación del dominio en español;
  comentarios solo donde aporten (invariantes, protocolo).
- Commits: los commits históricos de investigación conservan prefijos de fase
  (`G0-*`, `G1-*`, `G2-*`, `P0-*`). El mantenimiento post-cierre usa prefijos
  descriptivos convencionales como `fix:`, `docs:` o `chore:`.
- Nuevas hipótesis de extracción o reviewer assistance no reabren los gates
  sellados: deben plantearse como una fase nueva con preregistración propia.

## Conducta

Al participar en el proyecto aceptas `CODE_OF_CONDUCT.md`.

## Seguridad

Ver `SECURITY.md`.
