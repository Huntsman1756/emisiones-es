# G1-B Architecture — reuse-driven

Pipeline por documento:

```
SourceDocument
  │
  ▼
classification/dispatcher.py            [PORT_PATTERN: edgartools _424b + vc-statement-parser]
  DocumentClassification {
    acquisition_surface, document_role, scope_role,
    instrument_class, document_family, signals[], confidence }
  │  UNKNOWN -> REVIEW_REQUIRED, nunca best-guess
  ▼
extraction/dispatcher.py                [PORT_PATTERN: vc-statement-parser / sec-cli]
  family extractor por document_role:
    FINAL_TERMS      -> FinalTermsExtractor
    SECURITIES_NOTE  -> SecuritiesNoteExtractor
    ISSUE_DOC        -> IssueDocumentExtractor
    BASE_PROSPECTUS  -> BaseProspectusExtractor
    LIFECYCLE (supplement/correction/admission) -> pipeline de lineage, no contractual
  │
  ▼
extraction/common/locate.py             [PORT_PATTERN: sovereign-prospectus-corpus grep-first]
  CandidateRegion[] por seccion (interest/general/exercise/structured/...)
  │
  ▼
extraction/common/region_view.py        RegionView: vista acotada que conserva provenance
  │
  ▼
extraction/extractors.py  FIELD_SPECS   label->value + value_rx autocontenido
  - normalizadores deterministicos (normalize.py)
  - FieldSpec.multi -> lista OBSERVED (aspectos complementarios)
  - CONFLICT solo para valores que se contradicen sobre el mismo hecho
  - heuristico tabla: label repetido >=3 filas = columna de datos, no label
  │
  ▼
verification/verbatim.py                [PORT_PATTERN: sovereign-prospectus-corpus verify]
  raw_lexeme debe existir verbatim en excerpt/doc; si no -> VALUE_UNVERIFIED
  multi-valor: cada excerpt de evidencia verificado verbatim
```

## Linkage (family-first)

```
linking/family_linker.py                [PORT_PATTERN: edgartools ShelfLifecycle]
  family_key = nº registro oficial / NUMFOL / prefijo programa  (evidencia explicita)
  -> adjudicacion estructural (linking/rules.py)
  -> AUTO_LINKED | REVIEW_REQUIRED | NO_LINK
  tiempo solo ordena DENTRO de familia demostrada
```

## Lifecycle

```
lifecycle/__init__.py                   [PORT_PATTERN: edgartools]
  relaciones: SUPPLEMENTS, MODIFIES (gate-eligible)
  CORRECTS/REPLACES/REDEPOSIT: INSUFFICIENT_EVIDENCE (sin material observable)
```

## Terms canonicos

- `terms/daycount.py`  [ADOPT_DATA finos/CDM + REFERENCE QuantLib/Strata/regit]
- `terms/exercise.py`  [PORT_PATTERN QuantLib Callability shape]
- `terms/structured.py`[REFERENCE structured-products-toolkit/analytics]
- `terms/coupon.py`

## CUSTOM real (delta CNMV)

- anclas ES/EN de FIELD_SPECS y secciones por familia
- family keys CNMV (registro/NUMFOL/programa)
- heuristico data-column vs label-value
- reglas de adjudicacion estructural en linking/rules.py

## Safety invariants (dev)

- provenance 100% en observaciones aceptadas
- invented values = 0
- false AUTO_LINK = 0
- forced ambiguous -> auto = 0
- `Not found` es salida valida
- UNKNOWN/ambiguity -> REVIEW_REQUIRED, nunca forzado
