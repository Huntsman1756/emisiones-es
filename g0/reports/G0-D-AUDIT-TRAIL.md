# G0-D Audit Trail — incidencias de evaluación

Registro permanente de las dos incidencias ocurridas durante la evaluación
G0-D. Ninguna modificó código congelado ni predicciones selladas. El verdict
permanece **FAIL** en ambas versiones del truth.

## 1. Truth v1.0 → v1.1 (errata de anotación)

| versión | sha256 | notas |
|---|---|---|
| v1.0 (reconstruido) | `b323b7ad17f2a8f8fad809e6d6f13edac45de0075dcbf2b47266964930178aea` | `extraction-holdout-truth-v1.0.json`. Los bytes originales de v1.0 no se commitearon antes de la errata; reconstrucción semántica exacta = v1.1 − erratas |
| v1.1 (sellado) | `378567788c6ac17e36f72d1d255030ee5778f22eabd7db8a79ce7178fc541694` | `extraction-holdout-truth.json`. Es la versión de scoring y la commiteada |

### Diff semántico completo (v1.0 → v1.1)

```text
+ annotation_contract.errata: [ERRATA-1, ERRATA-2]  (metadatos)

X02: ranking        ABSENT → PRESENT
X02: subordination  ABSENT → PRESENT
X20: call_dates     ABSENT → NA
X20: put_dates      ABSENT → NA
```

### Evidencia de las correcciones

- **ERRATA-1 (X02)**: el documento contiene explícitamente
  `(i) Status of the Notes: | Senior Non-Preferred Notes` (página 2 del dump
  `X02_CCFF_11357_002.txt`, verificable con grep). El extractor había emitido
  `DERIVED 'SENIOR_NON_PREFERRED'` — correcto; con truth ABSENT se computaba
  FP. Dirección: **favorable** al sistema (FP→TP en `ranking`, +1 PRESENT en
  `subordination`).
- **ERRATA-2 (X20)**: el documento dice `Opción Emisor: No Aplicable.` /
  `Opción Inversor: No Aplicable.` (items 0084–0086 del dump
  `X20_CCFF_11340_019.txt`). Bajo `classify()`, truth NA + status MISSING → FN.
  Dirección: **desfavorable** al sistema (+2 FN en el grupo call_put).

Ambas correcciones son objetivamente verificables en el documento fuente — no
son reinterpretación de categorías tras ver resultados. Se encontraron durante
el análisis de errores post-scoring y se aplicaron con un **único re-scoring**.
El verdict es FAIL tanto con v1.0 como con v1.1.

## 2. Scorer de provenance — corrección de criterio (tooling de evaluación)

`tools/score_extraction_holdout.py`. Incidencia anterior al resultado oficial:
el primer diagnóstico reportó 194/258 valores con evidencia completa.

```text
ANTES:  exigía raw_lexeme top-level en cada field emitido
        → campos CONFLICT (raw en evidence[].excerpt) marcados como unbacked
        194/258

DESPUÉS: cada evidence item debe contener:
        source + snapshot_sha256 + page + extractor + (excerpt | raw_lexeme)
        → contrato real de la implementación congelada
        258/258 backed, 0 unsupported
```

La representación congelada almacena el lexema crudo en `evidence[].excerpt`,
no en `raw_lexeme` top-level — el criterio inicial era incorrecto, no la
provenance. Es una corrección del tooling de evaluación para implementar el
contrato preexistente; las predicciones selladas no se re-ejecutaron y el
fichero de predicciones (`2967a6f7…`) es idéntico antes y después.

## 3. Integridad general

```text
holdouts:          byte-idénticos antes/después (manifests + 30 PDFs)
predicciones:      selladas antes de truth/gold; nunca re-ejecutadas
código congelado:  sin modificaciones (HEAD a3179b9 → solo commits doc/results)
re-scorings:       1 (tras errata de truth); 0 tras cambios de código
verdict:           FAIL con v1.0 y con v1.1 — estable a las incidencias
```
