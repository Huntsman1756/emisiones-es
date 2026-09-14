# G1-B Parser families

Dispatcher de clasificacion (cascada auditable):

1. structured source metadata (acquisition_surface + denominacion)
2. explicit title/header en ventana acotada
3. required data anchors
4. document-specific signatures
5. layout/section signals
6. UNKNOWN

Roles: FINAL_TERMS, SECURITIES_NOTE, ISSUE_DOC, BASE_PROSPECTUS, SUPPLEMENT, CORRECTION, ADMISSION_RECORD, UNKNOWN.

## Extractores por familia

Todos comparten la interfaz `Extractor` (supports/locate/extract/verify/post_process/run) en `extraction/common/base.py`.

### FinalTermsExtractor (final_terms/)

CCFF CNMV. Secciones: interest, general, exercise, structured, redemption.
Label->value sobre textos + tablas; geometric lookup (value_right_of / label_below) para layout columnar.

### SecuritiesNoteExtractor (securities_note/)

Nota de valores (ADM deuda). Secciones equivalentes; anclas CNMV de nota.

### IssueDocumentExtractor (issue_doc/)

Documento de emision (ADM equity / otros). Terminos mas pobres; no fuerza campos.

### BaseProspectusExtractor (base_prospectus/)

Folletos base/emision. Extrae solo lo observable; placeholders `[[ ]]` no se promueven.

## Lifecycle pipeline (separado)

SUPPLEMENT/CORRECTION/ADMISSION no producen terminos contractuales; aportan lineage (lifecycle/ + family_linker).

## Reglas de extraccion transversales

- `Not found` valido: MISSING explicito
- `NOT_APPLICABLE` descartado si hay valor no-NA (el NA puede pertenecer a mecanismo alternativo)
- `cross_reference` ('See item X', 'As per Conditions') = evidencia real sin valor propio; no cuenta como extraido
- multi-aspecto (FieldSpec.multi): aspectos complementarios -> lista OBSERVED con evidencia por elemento
- CONFLICT: valores divergentes sobre el mismo hecho -> se conservan todos con evidencia
- verbatim: VALUE_UNVERIFIED si el lexema no se verifica en el documento
