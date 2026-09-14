# Modelo de venues e infraestructuras (España)

Fuente: "Relación de infraestructuras de mercados", CNMV
(`portal/consultas/rectoras/listadosim`), consultado 2026-09-14.

## Inventario registrado

| Sociedad rectora | Infraestructura | Tipología | Rol en el modelo |
|---|---|---|---|
| BME Markets & Exchanges, S.A. | Bolsa de Madrid | Mercado regulado | `Venue` (TRADED_ON / ADMITTED_TO) |
| Sociedad Rectora Bolsa de Barcelona | Bolsa de Barcelona | Mercado regulado | `Venue` |
| Sociedad Rectora Bolsa de Bilbao | Bolsa de Bilbao | Mercado regulado | `Venue` |
| Sociedad Rectora Bolsa de Valencia | Bolsa de Valencia | Mercado regulado | `Venue` |
| BME Markets & Exchanges | MEFF (productos derivados) | Mercado regulado | `Venue` |
| BME Markets & Exchanges | Mercado de Renta Fija AIAF | Mercado regulado | `Venue` — principal venue de deuda admitida vía CNMV |
| BME Markets & Exchanges | BME MTF Equity (+segmento BME Growth) | SMN | `Venue` |
| BME Markets & Exchanges | MARF | SMN | `Venue` — renta fija alternativa |
| BME Markets & Exchanges | Latibex | SMN | `Venue` (equity latam) |
| BME Markets & Exchanges | SENAF | SMN | `Venue` (deuda pública) |
| Archax Markets Europe, S.V., S.A. | DOWGATE MTF | SMN | `Venue` |
| European Digital Securities Exchange, S.V., S.A. | Portfolio Stock Exchange | SMN | `Venue` — LEI `959800UP9ANDBHTKJ408`, reg. CNMV 314 |
| CM Capital Markets Brokerage, S.V., S.A. | CAPI OTF | SOC | `Venue` |
| Corretaje e Información Monetaria y de Divisas, S.V., S.A. | CIMD OTF | SOC | `Venue` |
| Key Capital Partners Agencia de Valores, S.A. | VAMOS OTF | SOC | `Venue` |
| Tradition Financial Services España, S.V., S.A.U. | Tradition España OTF | SOC | `Venue` |
| Securitize Europe Brokerage and Markets, S.V., S.A. | SECURITIZE | SNL-TRD (DLT) | `Venue` + `SettlementArrangement` DLT (régimen piloto UE 2022/858) |
| Iberclear | Sistema de Liquidación ARCO | Depositario central | `SettlementArrangement` |
| BME Clearing | ECC | Contrapartida central | `SettlementArrangement` (clearing) |
| Sociedad de Bolsas | SIBE | Interconexión bursátil | Infraestructura de conectividad |

Nota corporativa: BME Renta Fija y BME Sistemas de Negociación fueron
absorbidas por BME Markets & Exchanges con efectos 2026-01-01; MEFF SR
Productos Derivados igualmente.

## Relaciones que el modelo debe distinguir

```text
ISSUED_BY    instrumento → emisor
ADMITTED_TO  instrumento → venue (admisión a negociación, acto formal)
TRADED_ON    instrumento → venue (negociación efectiva; puede ≠ admisión)
SETTLED_BY   instrumento → infraestructura de liquidación/registro
             (Iberclear ARCO, TARGET/PUENTE, SNL-TRD DLT, …)
```

`InstrumentVenue` materializa pares (instrumento, venue, rol, fechas,
fuente). Nunca colapsar estos cuatro roles en uno.

## Implicaciones para el corpus

- **AIAF/MARF** concentran la deuda con condiciones finales CNMV.
- **Portfolio Stock Exchange**: alta prioridad G0; hoy domina renta variable
  (SOCIMIs), pero el reglamento admite renta fija → seleccionar al menos un
  caso y documentar si solo hay equity.
- **SECURITIZE**: sin emisiones públicas confirmadas a 2026-09 → caso de
  diseño (reglamento + autorización CNMV) si no hay emisión documental.
- **OTFs** no incorporan emisiones propias; relevantes solo si aparecen como
  venue en filas CNMV/FIRDS.
- El modelo **no** asume settlement vía Iberclear: SECURITIZE liquida en DLT
  nativa; representable con `SettlementArrangement{type: DLT_TSS}`.
