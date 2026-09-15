# G2 — Canonical Document IR

IR común a la que se adapta la salida de cada backend. Los extractores
nunca se escriben contra un backend concreto.

```text
DocumentIR
    document_id
    pages[]

PageIR
    page_no
    width
    height
    blocks[]

BlockIR
    block_id
    block_type        # TEXT HEADING KEY VALUE TABLE TABLE_CELL
                      # LIST_ITEM FOOTNOTE OTHER
    text
    bbox              # coordenadas de página del backend, sin normalizar

    parent?
    children[]

    reading_order?

    table_id?
    row?
    column?

    heading_level?

    source_backend
    source_object_id
```

Reglas:

- No forzar estructura que el backend no produce. Campos desconocidos:
  `None`, nunca inferidos.
- `bbox` preserva la geometría nativa del backend (con su sistema de
  coordenadas documentado por adaptador). La IR es fiel, no uniforme a
  costa de perder información.
- `source_object_id` permite rastrear cada bloque al objeto nativo.

## Structural relations

Sobre la IR se representan relaciones explícitas:

```text
SAME_ROW
SAME_COLUMN
KEY_VALUE
UNDER_HEADING
NEXT_TO
CONTAINS
CONTINUATION_OF
FOOTNOTE_OF
```

Una relación proviene de **estructura del backend** o de **geometría
determinista** (p.ej. dos bloques en la misma fila de tabla). Nunca de una
interpretación financiera del extractor.

Separación estricta: `document structure` ≠ `financial semantics`. La IR
responde "qué está junto a qué"; la capa de claims responde "qué significa".
