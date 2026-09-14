# Gate G0-C — SCOUT IMPLEMENTATION

HEAD de partida: `a3e659eaba30146f638a8c0d85426a93d02756b9` (G0-B PASS).

## 1. Verificación del freeze (registrada al inicio y al cierre)

Hashes **completos** de los ficheros de manifest (sha256 del archivo):

| manifest | file sha256 | manifest_sha256 interno |
|---|---|---|
| `linkage-holdout.json` | `a36d37a32845b58f76b2bb75838f38653cb4728219f8bf84244c8e8250996b3f` | `e0f711bfa1de3c109c98d4ae4af35496aae17df2d11622b867fa57bb27bd1139` |
| `extraction-holdout.json` | `f44ce4d0c82fcae34ce493febe234cc85d7b0165e501a05878f2e5ffd1d23f1c` | `465a70efac101eb0439fd498434f18254e0241d835214cd96e527fcb9cbcdc74` |
| `linkage-scout.json` | `e7f2faf4ef3e2732ecf4d4ff30c366cb4d0b021f1e680018de2e2ef7a6b06785` | `99239b442bd1b70e9d086c83a112082f9ffcdedc5c451dad4053adf03dd2c359` |
| `extraction-scout.json` | `e90e4cc64efb85b6eec7dc8c50224c069277cf31348e4d606439a49ad33d8ed6` | `670ac8382753bce15fe30ecab1d86e9087b7af2585109e4e7379380ac7ed103c` |
| `g0-manifest.json` | `1df6165ea2d1f2eeb221b9ba340f746037302ac94497e90b70fcac457bf9ed7d` | — |

Conteos verificados: linkage scout 56, linkage holdout 300,
extraction scout 11, extraction holdout 30.

Los valores congelados viven en `g0/freeze-hashes.json` (generado por
`tools/check_freeze.py`) y el guard `tests/test_freeze_guard.py` falla
si cualquier manifest congelado o threshold preregistrado cambia.
Los archivos congelados **no se modificaron** para introducir el guard.

## 2. Separación scout/holdout endurecida

- El runner del linker (`tools/run_linkage_scout.py`) y el de extracción
  (`tools/run_extraction_scout.py`) leen **solo** los manifests scout.
- Las labels del linkage holdout están embebidas en el propio manifest
  congelado pero ningún código de runtime las carga; el guard verifica
  integridad, no contenido.
- Ningún resultado/threshold del holdout se ha calculado ni consultado.

## 3. Condiciones del gate

| Condición | Resultado |
|---|---|
| Holdouts byte-identicos | verificado inicio y cierre (ver informe) |
| Linker determinista/auditable | sí: registry de reglas explícitas, `docs/linking-rules.md` |
| 0 false positives scout (preferente) | **0 FP, 0 FN, 56/56** |
| Sin AMBIGUOUS forzado | 0 forzados; AMBIGUOUS solo por falta de evidencia estructural |
| Todo valor factual con evidencia reproducible | sí: `EvidencePointer` con page/bbox/text_excerpt Docling |
| 0 valores financieros inventados | sí: sin ancla → `MISSING`; placeholder de plantilla → `MISSING` |
| Baseline Docling determinista medido | `g0/results/docling-baseline.json` |
| Necesidad de ML tabular cuantificada | ver informe §6 |
| Reconciliación preserva conflictos | sí: `reconcile()` conserva todas las observaciones |
| Límites OSS respetados | guard de licencias en tests |

**Veredicto G0-C: PASS** (detalle en `g0/reports/G0-C-SCOUT-REPORT.md`).

La apertura de los dos holdouts requiere una fase separada y congelada.
