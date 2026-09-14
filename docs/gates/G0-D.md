# Gate G0-D — ONE-SHOT HOLDOUT EVALUATION

HEAD de partida: `a3179b9` (G0-C.1 PASS, code-freeze `5426194`).

**Veredicto: FAIL** — evaluación válida, 3 hard gates por debajo de
threshold. Informe completo: `g0/reports/G0-D-FINAL-EVALUATION.md`.

## 1. Verificación del freeze (inicio y cierre)

| manifest | file sha256 | estado |
|---|---|---|
| `linkage-holdout.json` | `a36d37a32845b58f76b2bb75838f38653cb4728219f8bf84244c8e8250996b3f` | idéntico antes/después |
| `extraction-holdout.json` | `f44ce4d0c82fcae34ce493febe234cc85d7b0165e501a05878f2e5ffd1d23f1c` | idéntico antes/después |
| 30 PDFs extraction | SHA individual por caso en manifest | byte-a-byte verificados |
| `code-freeze.json` | `58bf9d09b30dc58337fab35356c4ed5e77256e15e5992a1b928ced99eba44938` | sin cambios de código |

Pre-flight: 46/46 tests · linkage scout 56/56 · ambiguity-dev 18/18 ·
forced_ambiguous 0 · freeze guard PASS.

## 2. Predicciones selladas (antes de ver gold/truth)

| artefacto | sha256 |
|---|---|
| `g0-d-linkage-predictions.json` | `4345691d32f671129d9288b727bef0dd9be8051b7902e1ae3756dd2f880b88c1` |
| `g0-d-extraction-predictions.json` | `2967a6f7b657df76c27f7dbfb8eb8f29cd28e861af5860f1746bbbf48d422c17` |
| `extraction-holdout-truth.json` (v1.1, 2 erratas documentadas) | `378567788c6ac17e36f72d1d255030ee5778f22eabd7db8a79ce7178fc541694` |

Orden ejecutado: Docling full (KEEP_FULL) → extractores congelados → seal de
predicciones → anotación ciega de truth desde dumps de texto → scoring con el
contrato congelado (`deep_dev_metrics.classify`).

## 3. Resultado por gate

| Gate | Resultado | Threshold | Veredicto |
|---|---|---|---|
| Linkage accuracy | 88.33% | ≥ 98% | **FAIL** |
| Linkage precision | 100% | ≥ 99% | PASS |
| Linkage recall | 88.84% | ≥ 95% | **FAIL** |
| FP links / forced ambiguous | 0 / 0 | 0 / 0 | PASS |
| coupon/rate precision | 93.3% | ≥ 95% | **FAIL** |
| day_count precision | 93.75% | ≥ 95% | **FAIL** |
| maturity precision | 100% | ≥ 99% | PASS |
| call/put precision | 77.8% | ≥ 90% | **FAIL** |
| reset/fixing precision | 92.3% | ≥ 90% | PASS |
| observation precision | 100% | ≥ 90% | PASS |
| barrier/strike/redemption precision | 100% | ≥ 90% | PASS |
| Provenance | 258/258 backed, 0 invented | 100% | PASS |
| Novelty OSS_DELTA | 21/30 = 70% | ≥ 24/30 (80%) | **FAIL** |
| Freeze integrity | intacto | intacto | PASS |

Linkage fallos: S4 succession 25 (`MISSING_EXPLICIT_REFERENCE`), S7 rol 8 +
S9 2 (`RULE_DEFECT`). Extraction: fallos concentrados en recall y en clases
acotadas (absorción de label adyacente, conflación ranking/subordination,
formatos no-CCFF). Novelty: 0/9 en documentos no-definitorios (supplements,
corrections, registration, admissions, CP) + X28 (formato securities note no
cubierto); 100% en documentos definitorios de instrumento.

## 4. Estado del proyecto

```text
G0-A DISCOVERY              PASS
G0-B ACQUISITION/FREEZE     PASS
G0-C SCOUT                  PASS
G0-C.1 HARDENING            PASS
G0-D HOLDOUT EVALUATION     FAIL
```

El FAIL es el resultado del experimento: el núcleo determinista es seguro
(0 enlaces forzados, 0 valores sin evidencia, 0 inventados) pero la cobertura
de reglas/extractores y el delta documental sobre el corpus preregistrado no
alcanzan los umbrales. Remediación: fuera del scope de G0-D; candidatos para
una fase posterior (ver informe, sección POST-HOC).
