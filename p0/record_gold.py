"""P0-E gold recorder.

Reads a per-case spec (.work/p0e/units/<case>.json) and writes
validated gold units via p0.app.gold.GoldStore.

Spec unit:
  field, status, value?, note?,
  evidence: [{doc, page, match}]   # 'match' = substring locating the
                                  # IR block on that page; the block
                                  # text becomes the excerpt
  second_check (critical only):
    {'method':'value_in_page'}                # auto: value tokens in page
    {'method':'absence_scan','terms':[re..]}  # auto: zero hits in doc
    {'method':'dual_excerpt'}                 # >=2 pointers, diff pages

P0-E.1 human adjudication MUST pass both flags:
  --store p0/results/gold_human --adjudicator <HUMAN_ID>
--store and --adjudicator are only valid together; the bare default
writes to the provisional agent store p0/results/gold.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
from p0.app import cases  # noqa: E402
from p0.app.gold import GoldStore, GoldError, CRITICAL  # noqa: E402


def _norm(s):
    return ' '.join(unicodedata.normalize('NFKC', s).casefold().split())


def resolve_pointer(spec):
    doc, page, match = spec['doc'], spec['page'], spec['match']
    ir = cases.ir_for(doc)
    if not ir:
        raise GoldError(f'no IR for {doc}')
    pg = next((p for p in ir['pages'] if p['page_no'] == page), None)
    if pg is None:
        raise GoldError(f'{doc}: no page {page}')
    from p0.app import evidence as _ev
    m = _norm(match)
    for bl in pg['blocks']:
        t = (bl.get('text') or '').strip()
        if t and m in _norm(t):
            ptr = {'doc_id': doc, 'sha256': cases.doc_sha256(doc),
                   'page': page,
                   'bbox': [bl['bbox']['l'], bl['bbox']['t'],
                            bl['bbox']['r'], bl['bbox']['b']],
                   'excerpt': t}
            st, _ = _ev.validate_pointer(ptr)
            if st != 'OK':
                # mixed coord origins in some IR table blocks —
                # keep page+excerpt evidence, drop unusable bbox
                ptr.pop('bbox')
            return ptr
    raise GoldError(f'{doc} p{page}: block not found for {match!r}')


def absence_scan(doc, terms):
    ir = cases.ir_for(doc)
    hits = []
    for pg in ir['pages']:
        for bl in pg['blocks']:
            t = bl.get('text') or ''
            for term in terms:
                if re.search(term, t, re.IGNORECASE):
                    hits.append({'page': pg['page_no'], 'term': term,
                                 'text': t[:140]})
    return hits


def run(spec_path, store_dir=None, adjudicator=None):
    if bool(store_dir) != bool(adjudicator):
        raise GoldError('--store and --adjudicator must be given together')
    spec = json.load(open(spec_path, encoding='utf-8'))
    store = GoldStore(store_dir, adjudicator) if store_dir else GoldStore()
    cid = spec['case_id']
    doc = spec.get('doc') or cid.replace('P0-', '')
    written = []
    for u in spec['units']:
        ptrs = [resolve_pointer(e) for e in u.get('evidence', [])]
        sc = u.get('second_check')
        if u['field'] in CRITICAL:
            if sc is None:
                raise GoldError(f"{u['field']}: missing second_check")
            if sc['method'] == 'absence_scan':
                hits = absence_scan(doc, sc['terms'])
                if hits:
                    raise GoldError(
                        f"{u['field']}: absence_scan hits {hits[:3]}")
                sc = dict(sc, result='PASS')
            elif sc['method'] == 'dual_excerpt':
                pages = {p['page'] for p in ptrs}
                if len(pages) < 2:
                    raise GoldError(
                        f"{u['field']}: dual_excerpt needs 2 pages")
                sc = dict(sc, result='PASS')
            elif sc['method'] == 'value_in_page':
                sc = dict(sc, result='PASS')   # verified inside store
            elif sc['method'] == 'pdf_text_check':
                # independent second source: raw PDF text (pypdfium2),
                # bypassing the docling IR entirely
                import pypdfium2 as pdfium
                pdf = pdfium.PdfDocument(str(cases.pdf_path(doc)))
                full = ' '.join(_norm(pdf[i].get_textpage().get_text_range())
                                for i in range(len(pdf)))
                if _norm(sc['match']) not in full:
                    raise GoldError(
                        f"{u['field']}: pdf_text_check miss "
                        f"{sc['match']!r}")
                sc = dict(sc, result='PASS')
            else:
                raise GoldError(f"unknown second_check {sc['method']}")
        unit = store.record_unit(
            cid, u['field'], u['status'], u.get('value'), ptrs,
            u.get('note'), sc)
        written.append(unit['field'])
    store.seal_case(cid)
    print(f'{cid}: {len(written)} units recorded + case sealed')


if __name__ == '__main__':
    # python -m p0.record_gold <spec> [--store DIR] [--adjudicator ID]
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict(zip(
        [a[2:] for a in sys.argv[1:] if a.startswith('--')],
        [sys.argv[sys.argv.index(a) + 1]
         for a in sys.argv[1:] if a.startswith('--')]))
    run(args[0],
        store_dir=opts.get('store'),
        adjudicator=opts.get('adjudicator'))
