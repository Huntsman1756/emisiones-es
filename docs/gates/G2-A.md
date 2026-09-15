# G2-A — DOCUMENT BACKEND & SEMANTIC EVIDENCE RESEARCH

**Estado: OPEN** — fase de investigación. No es una evaluación; no produce
verdict PASS/FAIL de producto. Abre tras `g1-final-fail` (`0dc9e66`).

## 0. Posición heredada de G1-C

```text
Product opportunity       PROVEN            82% novelty (CI95 0.73–0.89)
Data acquisition          PROVEN
Document identity         PROVEN
Lifecycle                 PARTIALLY PROVEN  (SUPPLEMENTS P=R=1.0)
Safe linkage              PROVEN            P=1.0, false_auto=0
Deep term extraction      NOT PROVEN
Cold-template generaliz.  FAILED            coupon_rate cold R=0.04
Semantic claim safety     FAILED            invented=101 con provenance=1.0
Performance at scale      NOT ADDRESSED
```

G1-C separó oportunidad de capacidad: la información diferencial existe y
la vía conservadora (linkage, lifecycle) funciona; lo que falla es la
extracción profunda sobre layouts no vistos y la suficiencia semántica de
la evidencia.

El hallazgo clave: `provenance=100%` con `invented=101` demuestra que la
verificación actual prueba **presencia textual**, no **soporte semántico
del campo asignado**. Ese es el defecto arquitectónico a corregir.

## 1. Transición de datos

- Los cuatro holdouts G1 (linkage 124, extraction 97, lifecycle 49,
  novelty 100) están **consumidos** — fueron abiertos una sola vez bajo
  one-shot. Pasan íntegros a **DEVELOPMENT**: pueden usarse para
  iterar, medir backends y diseñar el verificador.
- G1 **no se reejecuta**. Ningún resultado futuro sobre esos casos puede
  llamarse evaluación G1 ni producir un verdict G1.
- El **holdout G2 no se selecciona ni se inspecciona** durante G2-A.
  Solo se preregistra y muestrea si la investigación justifica una nueva
  ronda (ver §7).

## 2. Hipótesis G2

> Convertir estructuras documentales heterogéneas en **afirmaciones
> financieras tipadas** cuya evidencia demuestre semánticamente el campo,
> independientemente de la plantilla del emisor.

Anti-objetivo declarado: **no** construir `+30 regex / +20 labels CNMV /
+10 excepciones por emisor`. Eso produce un parser de plantillas, que es
exactamente lo que G1-C demostró que no generaliza.

## 3. Semantic evidence — `ClaimEvidence`

La evidencia deja de ser "span que contiene el lexema" y pasa a ser una
relación estructural verificable:

```text
ClaimEvidence
    field
    normalized_value
    source_span
    source_page
    bbox
    semantic_anchor        # p.ej. "Business Day Convention"
    structural_relation    # p.ej. SAME_TABLE_ROW_VALUE
    context_scope          # sección/cláusula que gobierna el claim
    negative_context       # evidencia que lo invalidaría
    verification_status    # SUPPORTED | REVIEW | REJECT
```

Regla: `"Modified Following"` apareciendo en otra cláusula del documento
**ya no basta**. La presencia del lexema sin ancla semántica ni relación
estructural correcta no es SUPPORTED. Esto ataca directamente los 101
invented de G1-C.

Arquitectura objetivo:

```text
PDF
 │
 ├── Docling
 ├── PP-StructureV3
 └── deepdoctection
        │
        ▼
Canonical Document IR
        │
        ▼
semantic structures
 ├── key/value
 ├── table row/column
 ├── section scope
 ├── heading/value
 └── clause block
        │
        ▼
candidate financial claims
        │
        ▼
TYPED CLAIM VERIFIER
 ├─ semantic anchor?
 ├─ structural relation?
 ├─ correct document scope?
 ├─ financial type compatible?
 ├─ negative evidence?
 └─ normalization valid?
        │
        ▼
SUPPORTED | REVIEW | REJECT
```

La unidad de innovación pasa de "extraer strings" a **probar claims**.

## 4. Backend bake-off (trabajo central de G2-A)

Candidatos — todos Apache-2.0, REUSE FIRST se mantiene:

| backend | rol | notas |
|---|---|---|
| **Docling** | incumbent | baseline actual (2.126.0) |
| **PaddleOCR PP-StructureV3** | challenger | layout + table recognition + reading order + salida estructurada |
| **deepdoctection** | challenger | framework Document AI: layout/OCR/tablas/document understanding |
| LayoutParser | referencia | última release 2022; no candidato a backend, solo comparación conceptual |

Se mide sobre el corpus G1-development (97 extraction docs + slices
COLD_ISSUER), específicamente:

```text
table cell association
label/value association
reading order
cross-page tables
cold-issuer extraction
evidence geometry          # ¿el IR retiene anchor+relation+bbox usable?
runtime / RAM
```

**No** se mide OCR accuracy genérica ni métricas de benchmark público: la
pregunta es qué backend produce una IR en la que un claim tipado pueda
verificarse.

Nota de entorno (spike inicial):

- **PP-StructureV3**: viable — `paddlepaddle` 3.x publica wheels CPU
  Windows para Python 3.9–3.13 (índice propio de paquetes); el venv
  del proyecto es 3.13. Requiere PaddleOCR 3.x encima.
- **deepdoctection**: viable en modo reducido — desde que el paquete
  base ya no exige Detectron2 puede correr con HF Transformers/timm +
  DocTr + pdfplumber en Windows; la ruta Detectron2 sigue siendo
  Linux-first y se evita. Riesgo: soporte Windows no probado por
  upstream ("we haven't tried on Windows").
- **LayoutParser**: referencia solamente (release 2022).

Los backends challenger son dependencias pesadas. El bake-off vive en un
entorno de investigación aislado — **no** entra en
`requirements-lock.txt` ni en el árbol `src/` mientras no haya decisión
de adopción.

## 5. Structured products

G1-C confirma que structured products necesitan modelos de entidad, no
campos sueltos (`barrier_strike_redemption P=0.41`, `autocall P=0.04`).
Antes de scoring por campo se reconstruye la entidad coherente:

```text
StructuredPayoff
    underlying
    observation_schedule
    autocall   (trigger, redemption)
    coupon     (rate, barrier, memory)
    protection (barrier, strike, loss_formula)
    settlement
```

y se verifican invariantes entre sus componentes. Objetivo: reducir la
atribución cruzada que generó los falsos positivos.

## 6. Políticas heredadas

- **Linker: casi congelado.** P=1.0, false_auto=0, review_rate=53% es
  "sabe cuándo no sabe" — propiedad deseable en producto regulatorio.
  G2 puede trabajar coverage de linkage pero **no sacrifica esa
  precisión** para recuperar el 41% de recall faltante.
- **Performance: no se optimiza todavía.** Orden: semantic correctness →
  cold-layout generalization → safety → performance. Docling p50~49s es
  un problema de backfill futuro, no de esta fase.

## 7. Kill criterion (preregistrado para G2)

```text
Si después del cambio estructural:
  cold-issuer deep-term recall sigue bajo
  o unsupported claims > 0
  sin depender de plantillas por emisor:

  STOP general-purpose extraction.
```

En ese escenario el producto sobrevive como **security/document graph +
reference data + human-review extraction**, no como extractor contractual
automático general. No se concede una tercera ronda a una arquitectura
basada en matching de etiquetas/layout.

## 8. Criterio de salida de G2-A → preregistro G2

Solo se preregistra G2 (y se selecciona holdout nuevo) si la
investigación muestra que el cambio estructural **mejora
sustancialmente el slice COLD_ISSUER** sobre development G1 —
específicamente recall de términos profundos — manteniendo
`unsupported = 0`. Sin esa señal, se aplica el kill criterion.

## 9. Alcance de esta fase

G2-A produce: bake-off de backends, IR canónica candidata, diseño de
`ClaimEvidence` + verificador tipado, y medición COLD_ISSUER sobre
development. **No produce**: cambios de scoring contract, nuevos
thresholds, ni ningún verdict de producto.

## 10. VEREDICTO G2-A (2026-09-15, commit posterior a 80bb73c)

```text
G2-A VERDICT: FAIL segun criterios preregistrados -> kill criterion ACTIVADO
```

### Resultados

```text
Backend bake-off:
    Docling (baseline)     KEEP_DOCLING   IR 97/97, mejor TP-survival
    PP-StructureV3         STOP           ~57-73s/pag CPU (~70-100x),
                                          celdas sin bbox -> sin provenance celda
    deepdoctection         NO_BACKEND_IMPROVES  viable pero sin ventaja semantica;
                                          TP-survival peor (word-level)
    LayoutParser           REFERENCE_ONLY

Invented reanalysis (verificador tipado v2, docling IR, 101 claims):
    FIXED_TO_REJECT        65
    FIXED_TO_REVIEW        17
    STILL_FALSE_SUPPORTED  19   <- hard objective = 0: NO alcanzado

TP-control (778 EXACT de G1):
    UNCHANGED              303   WEAKENED_TO_REVIEW 213   LOST 262

COLD_ISSUER (10 docs stage1):
    instancias PRESENT criticas       44
    anchor en posicion de label       24/44 (55%)
    anchor en cualquier posicion      39/44 (89%)
    coupon_rate label-anchor          1/10 docs
    -> mejora de recall por cambio estructural: ~0
```

### Por que falla

1. El backend no es el cuello: docling y dd exponen el mismo texto; los
   residuales son clases semanticas identicas en ambos.
2. `invented=0` no se alcanza: 19 residuales recurrentes
   (convention-in-prose, boilerplate redemption, title-status, sub-field
   attribution) — requieren claim-schemas de campo y/o alineacion del
   contrato de anotacion, no mejor estructura.
3. Cold-issuer recall no mejora por estructura: la restriccion es
   cobertura de vocabulario de campo (e.g. Caixabank 'Interes Nominal
   Anual' no casa anchors canonicos). Extender vocabulario por familia
   de emisor = ruta de plantillas excluida por contrato.
4. Caveat honesto: varios residuales son frontera ambigua del gold
   (termino publicado en prosa marcado ABSENT) — posible truth-errata;
   el cero absoluto requeriria revisar el contrato de anotacion.

### Recomendacion

```text
STOP_GENERAL_EXTRACTION
```

Conforme al contrato preregistrado: `unsupported=0` no demostrado y
cold-issuer deep-term recall no mejora materialmente sin reglas por
emisor. El producto validado sobrevive como:

```text
security/document graph + reference data + safe linkage (P=1.0, FP=0)
+ novelty 82% demostrada + extraccion con human-review
```

Una via residual no probada existe — reconocimiento semantico de campo
sobre labels arbitrarios (ontologia canonica / clasificador, no
plantillas por emisor) — pero seria una hipotesis nueva, fuera del
alcance demostrado de G2-A.

Holdout G2: no seleccionado ni inspeccionado. G0/G1 permanecen frozen.
