# G1-B Canonical terms

## DayCountCanonical (terms/daycount.py)

Tabla versionada de convenciones: `canonical_id` (estilo CDM `DayCountFractionEnum`), aliases de lexema ES/EN, referencia de estandar (ISDA 2006 §4.16 / ICMA Rule 251).

Soportadas: 1/1, ACT/ACT, ACT/ACT ICMA, ACT/ACT ISDA, ACT/360, ACT/365, ACT/365F, 30/360, 30E/360, 30E/360 ISDA.

Regla: `1/1` es convencion real (ISDA) — el fallo G0 fue de contexto. Se exige contexto de seccion aplicable; nunca inferir por defecto.

## ExerciseTerms (terms/exercise.py)

```
ExerciseTerms {
  option_side: CALL | PUT          # emisor vs inversor
  exercise_dates[]
  exercise_window?
  exercise_price?, price_type?
  notice_period?, conditions?
  evidence[]
}
```

Shape: QuantLib `Callability{price, Type{Call,Put}, date}` + `CallabilitySchedule`.
Vistas derivadas `call_dates`/`put_dates` para compatibilidad de scoring.

Deteccion ES: `Opcion (del) Emisor` -> CALL, `Opcion (del) Inversor` -> PUT, `amortizacion anticipada por/para el emisor|inversor`.

## StructuredProductTerms (terms/structured.py)

Campos separados por rol semantico (REFERENCE: structured-products-toolkit / structured-products-analytics):

- `autocall_trigger` — cancelacion automatica anticipada
- `coupon_barrier` — barrera de cupon (pago condicionado)
- `protection_barrier` — barrera de proteccion a vencimiento
- `underlying[]`, `initial_level`/`strike`
- `observation_schedule`
- `coupon { rate, barrier, memory }`
- `participation`, `cap`, `settlement_type`

El campo plano `barrier` del scoring dev no debe colapsar los 3 roles; la separacion canonica vive en este modelo.

## CouponTerms (terms/coupon.py)

```
CouponTerms {
  coupon_type: FIXED | FLOATING | FIXED_TO_FLOATING | STEP_UP | ZERO | STRUCTURED | OTHER
  fixed_rate?, benchmark?, spread?
  reset_schedule?, fixing_rules?
  floor?, cap?
  payment_frequency?, day_count?
}
```

Solo categorias con evidencia en DEVELOPMENT; no completar el enum por completarlo.

## Multi-valor

Campos multi-aspecto (`fixing_rules`, `redemption_formula`, `observation_dates`, `reset_dates`, `call_dates`, `put_dates`, `underlying`, `barrier`, `autocall`, `business_day_convention`, `coupon_type`, `coupon_rate`, `payment_frequency`, `spread`, `benchmark`, `settlement_type`): aspectos complementarios -> lista OBSERVED. `CONFLICT` reservado a contradiccion sobre el mismo hecho.
