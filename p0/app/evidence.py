"""Evidence pointer validation (P0-B §10)."""
import hashlib
import math
import unicodedata

from . import cases


def validate_pointer(pointer, allowed_documents=None):
    if not isinstance(pointer, dict):
        return 'BROKEN_EVIDENCE', 'pointer must be an object'
    doc = pointer.get('doc_id')
    if not cases.valid_doc_id(doc):
        return 'BROKEN_EVIDENCE', 'document not found: invalid id'
    if allowed_documents is not None and doc not in allowed_documents:
        return 'BROKEN_EVIDENCE', 'document not authorized for case'
    page = pointer.get('page')
    if type(page) is not int or page < 1:
        return 'BROKEN_EVIDENCE', 'page must be a positive integer'
    bbox = pointer.get('bbox')
    if bbox is not None and (
            not isinstance(bbox, (list, tuple)) or len(bbox) != 4 or
            any(type(x) not in (int, float) or not math.isfinite(x)
                for x in bbox)):
        return 'BROKEN_EVIDENCE', 'bbox must contain four finite numbers'
    excerpt = pointer.get('excerpt')
    if excerpt is not None and not isinstance(excerpt, str):
        return 'BROKEN_EVIDENCE', 'excerpt must be text'
    declared = pointer.get('sha256')
    if declared is not None and (not isinstance(declared, str) or
                                 len(declared) != 64 or
                                 any(c not in '0123456789abcdef' for c in declared)):
        return 'BROKEN_EVIDENCE', 'invalid sha256'
    try:
        pdf = cases.pdf_path(doc)
        if pdf is None:
            return 'BROKEN_EVIDENCE', f'document not found: {doc}'
        actual = hashlib.sha256(pdf.read_bytes()).hexdigest()
        known_sha = cases.doc_sha256(doc)
        if known_sha and actual != known_sha:
            return 'BROKEN_EVIDENCE', 'snapshot sha256 mismatch'
        if declared and declared != actual:
            return 'BROKEN_EVIDENCE', 'sha256 mismatch vs source'
        ir = cases.ir_for(doc)
        if ir:
            pages = {p['page_no']: p for p in ir['pages']}
            if page not in pages:
                return 'BROKEN_EVIDENCE', f'page {page} out of range'
            pg = pages[page]
            width, height = pg['width'], pg['height']
            page_text = ' '.join(bl.get('text') or '' for bl in pg['blocks'])
        else:
            from pypdf import PdfReader
            reader = PdfReader(str(pdf))
            if page > len(reader.pages):
                return 'BROKEN_EVIDENCE', f'page {page} out of range'
            pg = reader.pages[page - 1]
            width, height = float(pg.mediabox.width), float(pg.mediabox.height)
            page_text = pg.extract_text() or ''
        if bbox is not None:
            l, t, r, b = bbox
            if not (0 <= l < r <= width * 1.02 and
                    0 <= b < t <= height * 1.02):
                return 'BROKEN_EVIDENCE', 'bbox outside page bounds'
        if excerpt and _norm(excerpt) not in _norm(page_text):
            return 'BROKEN_EVIDENCE', 'excerpt not present in page text'
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError):
        return 'BROKEN_EVIDENCE', 'source evidence could not be verified'
    return 'OK', None


def _norm(s):
    return ' '.join(unicodedata.normalize('NFKC', s).casefold().split())


def audit_case(case_id, pointers, allowed_documents=None):
    if allowed_documents is None:
        case = cases.all_cases().get(case_id)
        allowed_documents = cases.document_ids(case) if case else set()
    out = []
    for p in pointers:
        status, detail = validate_pointer(p, allowed_documents)
        wrong_doc = bool(detail and ('document not found' in detail or
                                     'document not authorized' in detail))
        out.append({'pointer': p, 'status': status, 'detail': detail,
                    'wrong_document': wrong_doc})
    ok = sum(1 for o in out if o['status'] == 'OK')
    return {
        'case_id': case_id, 'total': len(out), 'ok': ok,
        'navigation_rate': ok / len(out) if out else None,
        'wrong_document_links': sum(1 for o in out if o['wrong_document']),
        'results': out,
    }
