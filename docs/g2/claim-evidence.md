# G2 — ClaimEvidence & Support Contract

Objeto de investigación central de G2. Un claim financiero solo es
`SUPPORTED` cuando la evidencia demuestra semánticamente el campo, no
cuando un texto plausible existe cerca.

```text
ClaimEvidence
    field
    normalized_value

    source_document
    source_page
    source_block_ids[]

    raw_lexeme

    semantic_anchor
    structural_relation
    context_scope

    negative_context[]

    verification_status:  SUPPORTED | REVIEW | REJECT

    verifier_rule
    verifier_version
```

Una cita textual por sí sola **no** es `SUPPORTED`.

## Support contract

`SUPPORTED` exige simultáneamente:

```text
1. value present in evidence
2. valid semantic anchor
3. valid structural relation
4. compatible document/section scope
5. canonical field type compatible
6. no disqualifying negative context
```

Ejemplo: `BUSINESS_DAY_CONVENTION = MODIFIED_FOLLOWING` es válido si existe
algo equivalente a `"Business Day Convention"` — SAME_ROW/KEY_VALUE —
`"Modified Following"`. No es válido si `Modified Following` aparece en
una cláusula distinta sin vínculo estructural con el campo.

## Negative context

Reglas explícitas construidas sobre casos DEVELOPMENT de invención G1.
Prioridad inicial (top fields de los 101 invented):

```text
redemption_formula
business_day_convention
ranking
coupon_type
day_count
```

Clases de contexto negativo observadas:

```text
portfolio disclosure table
historical information
risk-factor prose
definition unrelated to instrument terms
example/calculation only
generic base-prospectus template
column header describing underlying assets
```

No son una blacklist universal: cada regla debe estar soportada por casos
development concretos y produce `REJECT` o `REVIEW`, nunca silencio.
