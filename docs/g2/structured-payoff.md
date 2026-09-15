# G2 — Entity-first StructuredPayoff

G1-C: los campos estructurados extraídos de forma independiente producen
atribución cruzada (barrier de una cláusula + redemption de otra +
underlying de otra serie = instrumento ficticio). `autocall P=0.04`,
`barrier_strike_redemption P=0.41`.

G2 reconstruye primero una entidad coherente; los campos se verifican
como componentes de la entidad, no como búsquedas independientes:

```text
StructuredPayoff
    underlying[]

    observation_schedule

    autocall:
        trigger
        dates
        redemption

    coupon:
        rate
        barrier
        memory

    protection:
        barrier
        strike
        loss_formula

    participation
    cap

    settlement_type
```

Reglas:

- Un componente solo entra en la entidad si su `context_scope` pertenece
  a la misma unidad contractual (misma sección de payoff, misma tabla,
  misma clause block — según relaciones IR).
- Invariantes a verificar tras ensamblado: p.ej. autocall trigger implica
  observation schedule; protection barrier < strike; settlement_type
  compatible con loss_formula.
- Un componente sin ancla estructural a la entidad → `REVIEW`, nunca
  asignado por proximidad.
