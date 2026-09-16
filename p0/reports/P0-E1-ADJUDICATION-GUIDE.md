# P0-E.1 — Guía de adjudicación (JOINT_REVIEWER_A_B)

## Fase 1 — anotación independiente

Cada reviewer rellena **sus 30 specs** sin consultar al otro:

- REVIEWER_A → `.work/p0e1/specs/A/P0-ADM_*.json`
- REVIEWER_B → `.work/p0e1/specs/B/P0-ADM_*.json`

Fuentes permitidas — **únicamente**:

- PDF CNMV congelado del caso (`cases.pdf_path(doc)`);
- el dump de texto `.work/p0e/P0-ADM_*.txt` (texto IR del mismo PDF);
- metadata oficial CNMV congelada del caso.

Prohibido decidir gold con: Bloomberg, Refinitiv, Google, machine
candidates, gold del agente, ni tus propios reviews P0-D (no abrir
`p0/results/p0d/` ni `p0/results/gold/`).

## Cómo rellenar cada campo (28 por spec)

```json
{"field": "isin", "status": "CONFIRMED_VALUE",
 "value": "ES0...",
 "evidence": [{"doc": "ADM_...", "page": 2, "match": "texto literal del doc"}],
 "note": "opcional",
 "second_check": {"method": "pdf_text_check", "match": "ES0..."}}
```

- `status`: `CONFIRMED_VALUE` · `CONFLICT` · `MISSING` · `NOT_APPLICABLE`.
- `CONFIRMED_VALUE` exige `value` + ≥1 `evidence`.
- `CONFLICT` exige evidence de ambas lecturas.
- `match` = fragmento literal del texto fuente en esa página; el recorder
  resuelve página/bbox/excerpt automáticamente.
- Los 10 campos críticos (`isin, issuer, currency, maturity, issued_amount,
  coupon_type, coupon_rate, underlying, call_put_terms, redemption` —
  ver lista exacta en `p0/app/gold.py: CRITICAL`) requieren
  `second_check` con método:
  - `dual_excerpt` — 2 evidencias en páginas distintas;
  - `pdf_text_check` — `match` se busca en el texto bruto del PDF;
  - `absence_scan` — `terms` que NO deben aparecer;
  - `value_in_page` — tokens del valor presentes en la página apuntada.
- `MISSING`/`NOT_APPLICABLE` llevan `note`; críticos con esos estados
  pueden usar `absence_scan` como second check.

## Caso especial: P0-ADM_123067

El documento imprime dos ISIN distintos para el subyacente. No se
resuelve con fuentes externas: registrar `CONFLICT` (o lo que el contrato
de anotación exija) preservando ambas lecturas como evidencia.

## Fase 2 — sellado independiente

Cuando tus 30 specs estén completas, avisa. El operador grabará:

```text
python -m p0.record_gold <spec> --store p0/results/gold_human/<A|B> --adjudicator REVIEWER_<A|B>
```

## Fase 3 — discrepancias + auditoría de acuerdos

- 100% de discrepancias A↔B se resuelven **conjuntamente** en
  `.work/p0e1/joint/P0-ADM_*.json` (mismo formato de spec).
- Además se audita una muestra del 20% de unidades coincidentes
  (seed derivada del protocol SHA, registrada).
- El truth final (`JOINT_REVIEWER_A_B`) = acuerdos + resoluciones
  conjuntas, sellado como `truth-human-v1`.

## Regla de oro

Un valor sin evidencia semántica suficiente → `MISSING`/`CONFLICT`,
nunca inferido. El texto cercano al campo no basta: la evidencia debe
soportar la relación label/valor/cláusula real.
