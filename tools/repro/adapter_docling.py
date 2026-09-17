"""Docling JSON -> DocumentIR. Fiel al backend; no infiere campos ausentes."""
from ir import DocumentIR, PageIR, BlockIR

LABEL_MAP = {
    "section_header": "HEADING", "title": "HEADING",
    "list_item": "LIST_ITEM", "footnote": "FOOTNOTE",
    "text": "TEXT", "caption": "TEXT", "paragraph": "TEXT",
    "formula": "TEXT", "page_header": "OTHER", "page_footer": "OTHER",
    "checkbox_selected": "OTHER", "checkbox_unselected": "OTHER",
    "picture": "OTHER", "document_index": "OTHER", "code": "TEXT",
    "form": "OTHER", "key_value_region": "OTHER", "grading_scale": "OTHER",
    "handwritten_text": "TEXT", "empty_value": "OTHER",
}


def _bbox(prov):
    if not prov:
        return None
    b = prov[0].get("bbox") or {}
    return {"l": b.get("l"), "t": b.get("t"), "r": b.get("r"),
            "b": b.get("b"), "coord_origin": b.get("coord_origin")}


def from_docling_json(d: dict, document_id: str) -> DocumentIR:
    doc = DocumentIR(document_id=document_id)
    pages = d.get("pages", {})
    items = list(pages.items()) if isinstance(pages, dict) else enumerate(pages, 1)
    pmap = {}
    for key, p in items:
        pi = PageIR(page_no=int(p.get("page_no", key)), width=p["size"]["width"],
                    height=p["size"]["height"])
        pmap[pi.page_no] = pi
        doc.pages.append(pi)

    def put(ref, label, text, prov, level=None, extra=None):
        page_no = prov[0]["page_no"] if prov else None
        page = pmap.get(page_no) or (doc.pages[0] if doc.pages else None)
        b = BlockIR(block_id=ref.lstrip("#/"), block_type=LABEL_MAP.get(label, "OTHER"),
                    text=text or "", bbox=_bbox(prov), heading_level=level,
                    source_backend="docling", source_object_id=ref)
        if extra:
            for k, v in extra.items():
                setattr(b, k, v)
        if page:
            page.blocks.append(b)
        return b

    for i, t in enumerate(d.get("texts", [])):
        b = put(t["self_ref"], t.get("label", ""), t.get("text"), t.get("prov"),
                level=t.get("level"))
        par = (t.get("parent") or {}).get("$ref")
        if par:
            b.parent = par.lstrip("#/")
    for i, t in enumerate(d.get("tables", [])):
        tid = f"tables/{i}"
        put(t["self_ref"], "table", "", t.get("prov"))
        data = t.get("data") or {}
        for ci, c in enumerate(data.get("table_cells", [])):
            cell = BlockIR(
                block_id=f"{tid}/cell/{ci}", block_type="TABLE_CELL",
                text=c.get("text") or "", bbox=_bbox([{"page_no": (t.get("prov") or [{}])[0].get("page_no"), "bbox": c.get("bbox")}]),
                table_id=tid, row=c.get("start_row_offset_idx"),
                column=c.get("start_col_offset_idx"),
                source_backend="docling", source_object_id=f"{tid}/cell/{ci}")
            cell.parent = tid
            pmap.get((t.get("prov") or [{}])[0].get("page_no"), doc.pages[0]).blocks.append(cell)
    for i, kv in enumerate(d.get("key_value_items", [])):
        kref = f"key_value_items/{i}"
        key = kv.get("key", {})
        val = kv.get("value", {})
        put(kref + "/key", "key_value_region", key.get("text"), key.get("prov"), extra={"table_id": kref})
        put(kref + "/val", "key_value_region", val.get("text"), val.get("prov"), extra={"table_id": kref})
    return doc
