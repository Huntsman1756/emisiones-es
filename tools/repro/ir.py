"""G2-A Canonical Document IR (investigacion — vive en .work/g2a, no en src/)."""
from dataclasses import dataclass, field, asdict

BLOCK_TYPES = {"TEXT", "HEADING", "KEY", "VALUE", "TABLE", "TABLE_CELL",
               "LIST_ITEM", "FOOTNOTE", "OTHER"}


@dataclass
class BlockIR:
    block_id: str
    block_type: str
    text: str
    bbox: dict | None = None          # {l,t,r,b,coord_origin}
    parent: str | None = None
    children: list = field(default_factory=list)
    reading_order: int | None = None
    table_id: str | None = None
    row: int | None = None
    column: int | None = None
    heading_level: int | None = None
    source_backend: str = ""
    source_object_id: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class PageIR:
    page_no: int
    width: float | None
    height: float | None
    blocks: list = field(default_factory=list)


@dataclass
class DocumentIR:
    document_id: str
    pages: list = field(default_factory=list)
    relations: list = field(default_factory=list)  # (type, a_id, b_id, origin)

    def to_dict(self):
        return {"document_id": self.document_id,
                "pages": [{"page_no": p.page_no, "width": p.width,
                           "height": p.height,
                           "blocks": [b.to_dict() for b in p.blocks]}
                          for p in self.pages],
                "relations": [{"type": t, "a": a, "b": b, "origin": o}
                              for t, a, b, o in self.relations]}


def derive_relations(doc: DocumentIR):
    """Relaciones deterministas sobre la IR: estructura/geometria, no semantica."""
    rel = doc.relations
    # orden global de lectura por aparicion en pages[]
    ordered = [b for p in doc.pages for b in p.blocks]
    for i, b in enumerate(ordered):
        b.reading_order = i
        if i:
            rel.append(("NEXT_TO", ordered[i - 1].block_id, b.block_id, "geometry"))
        if b.parent:
            rel.append(("CONTAINS", b.parent, b.block_id, "backend"))
    # tabla: SAME_ROW / SAME_COLUMN / KEY_VALUE(header->cell)
    by_table = {}
    for b in ordered:
        if b.block_type == "TABLE_CELL" and b.table_id:
            by_table.setdefault(b.table_id, []).append(b)
    for tid, cells in by_table.items():
        for a in cells:
            for c in cells:
                if a is c:
                    continue
                if a.row == c.row:
                    rel.append(("SAME_ROW", a.block_id, c.block_id, "table"))
                if a.column == c.column:
                    rel.append(("SAME_COLUMN", a.block_id, c.block_id, "table"))
    # UNDER_HEADING: bloques bajo un heading hasta el siguiente de nivel <=
    cur = None
    for b in ordered:
        if b.block_type == "HEADING":
            cur = b
        elif cur is not None:
            rel.append(("UNDER_HEADING", cur.block_id, b.block_id, "reading_order"))
    return doc
