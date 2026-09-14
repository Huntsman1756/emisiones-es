# Propuesta de corpus G0-C (preregistro)

Fecha: 2026-09-14. La lista concreta de `document_id`/URL/hash se congela al
descargar; este documento fija los **estratos y reglas de selección**, no
documentos inventados.

## Reglas de selección

1. Maximizar heterogeneidad: emisor, tipo de instrumento, venue, rol
   documental, idioma (ES/EN), plantilla de CCFF.
2. Cada documento debe descargarse de CNMV/venue con snapshot + hash.
3. Ningún documento entra sin URL fuente resoluble en el momento de congelar.
4. Si un estrato resulta vacío en el universo real (p.ej. DLT sin emisiones
   públicas), se documenta y se redistribuye el peso — no se fabrican casos.

## Estratos y candidatos orientativos

| # | Estrato | n | Candidatos orientativos (a verificar en descarga) |
|---|---|---|---|
| 1 | Bonos senior plain vanilla | 5 | CCFF de programas EMTN/bonos de Santander, CaixaBank, BBVA, Bankinter (AIAF); un no-bancario (p.ej. utility) en MARF |
| 2 | FRN | 4 | Flotantes Euribor+spread de banca española (AIAF); alguno MARF |
| 3 | Cédulas/covered bonds | 4 | Cédulas hipotecarias/territoriales de emisor español; AyT cédulas si aplica |
| 4 | Subordinados T2 | 2 | T2 bancarios recientes con cláusulas de call |
| 5 | AT1 | 2 | AT1 de banca española (docs típicamente EN; fixed rate reset → buen test de reset/fixing) |
| 6 | Estructurados | 5 | "BONOS/OBLIG. ESTRUCTURADOS" en tabla CCFF (autocallables sobre IBEX35/acciones; barreras; observation dates) |
| 7 | Suplementos | 3 | Suplementos a folletos base de programas usados en estratos 1–5 |
| 8 | Correcciones/redepósitos | 2 | Documentos marcados como rectificación/redepósito en CNMV |
| 9 | Multi-venue | 2 | Emisiones admitidas AIAF+MARF o con venue no-BME |
| 10 | Portfolio Stock Exchange | 1–2 | Documento informativo de incorporación; si no hay deuda, caso equity + nota de limitación |
| 11 | SECURITIZE/DLT | 0–1 | Emisión tokenizada si existe material público; si no: design-case (reglamento + autorización CNMV 2025-11-26) |

Total ≈ 30.

## Registro por documento

```text
doc_id, source, source_url, snapshot_hash, retrieved_at, role, issuer,
programme_ref, isin(s), venue(s), stratum, language, notes
```
