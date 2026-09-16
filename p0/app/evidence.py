"""Evidence pointer validation (P0-B §10).

A pointer is valid only if: document exists, SHA matches the frozen
input when known, page exists, bbox within page bounds, and the excerpt
is present in the source page text when provided.
"""
import hashlib

from . import cases


def validate_pointer(pointer):
    """Return (status, detail). status: OK | BROKEN_EVIDENCE."""
    doc = pointer.get('doc_id')
    pdf = cases.pdf_path(doc)
    if pdf is None:
        return 'BROKEN_EVIDENCE', f'document not found: {doc}'

    known_sha = cases.doc_sha256(doc)
    declared = pointer.get('sha256')
    if declared and known_sha and declared != known_sha:
        return 'BROKEN_EVIDENCE', 'sha256 mismatch vs frozen input'
    if known_sha:
        actual = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if actual != known_sha:
            return 'BROKEN_EVIDENCE', 'snapshot sha256 mismatch'

    ir = cases.ir_for(doc)
    page = pointer.get('page')
    bbox = pointer.get('bbox')
    if ir:
        pages = {p['page_no']: p for p in ir['pages']}
        if page not in pages:
            return 'BROKEN_EVIDENCE', f'page {page} out of range'
        pg = pages[page]
        if bbox:
            l, t, r, b = bbox
            if not (0 <= l <= r <= pg['width'] * 1.02 and
                    0 <= b <= t <= pg['height'] * 1.02):
                return 'BROKEN_EVIDENCE', 'bbox outside page bounds'

    excerpt = (pointer.get('excerpt') or '').strip()
    if excerpt and ir:
        page_text = ' '.join(
            (bl.get('text') or '') for bl in pages[page]['blocks'])
        if excerpt[:80] not in page_text:
            return 'BROKEN_EVIDENCE', 'excerpt not present in page text'
    return 'OK', None


def audit_case(case_id, pointers):
    """Validate every pointer; count wrong-document links separately."""
    out = []
    for p in pointers:
        status, detail = validate_pointer(p)
        wrong_doc = bool(detail and 'document not found' in detail)
        out.append({'pointer': p, 'status': status, 'detail': detail,
                    'wrong_document': wrong_doc})
    ok = sum(1 for o in out if o['status'] == 'OK')
    return {
        'case_id': case_id, 'total': len(out), 'ok': ok,
        'navigation_rate': ok / len(out) if out else None,
        'wrong_document_links': sum(1 for o in out if o['wrong_document']),
        'results': out,
    }
