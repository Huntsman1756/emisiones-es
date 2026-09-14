# G0-G — NOVELTY / OSS_DELTA

## Hipótesis bajo prueba

> ¿Aporta Emisiones ES información material que no exista ya estructurada en
> FIRDS/ESAP?

## Lo que FIRDS ya cubre (verificado contra RTS 23, tabla 3)

Para deuda: ISIN, FISN, CFI, LEI emisor, MIC venue, fechas de
solicitud/aprobación/admisión, importe nominal total, vencimiento, divisa,
nominal por unidad, **tipo fijo**, benchmark+spread de flotantes, seniority
(4 valores).

## Lo que FIRDS/ESAP no estructuran (delta esperado)

- Mecánica de cupón completa: frecuencia, day-count, business-day
  convention, fechas de reset, reglas de fixing.
- Call/put schedules, fórmulas de redención, amortización.
- Estructurados: underlying, strike, barreras, autocall, observation dates,
  participation, cap, settlement type.
- **Grafo documental**: base↔suplemento↔CCFF↔corrección↔redepósito↔admisión
  (linaje histórico de la emisión).
- Provenance a nivel de campo (página/bbox/span del documento fuente).
- Reconciliación multi-fuente con conflictos preservados.

## Criterio

```text
>= 80% de los instrumentos del corpus aportan >= 1 término contractual
material no estructurado en FIRDS/ESAP.
```

FAIL automático si el resultado real es esencialmente
`descargar FIRDS + parsear PDF + JSON`.

## Contra-evidencia detectada en G0-A (honestidad)

1. **Para plain vanilla senior, el delta puede ser fino**: FIRDS ya reporta
   tipo fijo, vencimiento, nominal, seniority → el valor diferencial se
   concentra en call/put, reset, structured y **document lineage**. El
   corpus está estratificado para sobre-representar instrumentos complejos;
   si la mezcla real del mercado español es >70% plain vanilla, el criterio
   del 80% podría medirse sobre un corpus no representativo — riesgo
   declarado, mitigado registrando el tipo de instrumento por caso.
2. **CNMV ya expone ISIN+mercado+tipo en tablas** de CCFF: el *indexado* no
   es diferencial; lo diferencial son términos y linaje.
3. **ESAP (fase 1, prospectus) entrará en 2027**: si ESAP publica documentos
   + metadatos, el valor se desplaza aún más hacia extracción de términos y
   grafo — el delta documental puede encoger, el de términos no.
4. **Portfolio Stock Exchange** hoy es mayoría equity/SOCIMIs → puede que no
   haya emisión de deuda que muestre el delta completo; se documenta como
   limitación del corpus.
5. **SECURITIZE** puede no tener emisión pública con documentación en la
   ventana del G0 → caso de diseño.

## Artefacto

`g0/reports/OSS_DELTA.md` listará por instrumento: términos extraídos,
presencia en FIRDS/ESAP (sí/no), y fuente de la evidencia.
