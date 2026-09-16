"""P0-E gold adjudication helpers (run as script or import).

  python -m p0.gold_tool dump P0-ADM_121210     # text dump -> .work/p0e/
  python -m p0.gold_tool find ADM_121210 "vencimiento"   # locate evidence

find() returns the IR blocks matching a regex so the adjudicator can
attach (page, bbox, excerpt) pointers that validate cleanly.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
from p0.app import cases  # noqa: E402

WORK = REPO / '.work' / 'p0e'


def dump_case(case_id, out_dir=WORK):
    case = cases.all_cases().get(case_id)
    if case is None:
        raise SystemExit(f'unknown case {case_id}')
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [f'# {case_id} isin={case.get("isin")} '
             f'issuer={case.get("issuer")} stratum={case.get("stratum")}']
    for doc in case['documents']:
        ir = cases.ir_for(doc)
        lines.append(f'## doc {doc} '
                     f'(ir={"yes" if ir else "no"})')
        if not ir:
            continue
        for pg in ir['pages']:
            lines.append(f'--- page {pg["page_no"]} '
                         f'{pg["width"]:.0f}x{pg["height"]:.0f}')
            for bl in pg['blocks']:
                t = (bl.get('text') or '').strip()
                if t:
                    lines.append(t)
    path = out_dir / f'{case_id}.txt'
    path.write_text('\n'.join(lines), encoding='utf-8')
    return path


def find(doc_id, pattern, max_hits=20):
    """Regex search over IR blocks -> pointer-ready dicts."""
    ir = cases.ir_for(doc_id)
    if not ir:
        return []
    rx = re.compile(pattern, re.IGNORECASE)
    hits = []
    for pg in ir['pages']:
        for bl in pg['blocks']:
            t = (bl.get('text') or '').strip()
            if t and rx.search(t):
                hits.append({
                    'doc_id': doc_id,
                    'sha256': cases.doc_sha256(doc_id),
                    'page': pg['page_no'],
                    'bbox': [bl['bbox']['l'], bl['bbox']['t'],
                             bl['bbox']['r'], bl['bbox']['b']],
                    'excerpt': t,
                })
                if len(hits) >= max_hits:
                    return hits
    return hits


def page_text(doc_id, page_no):
    ir = cases.ir_for(doc_id)
    for pg in ir['pages']:
        if pg['page_no'] == page_no:
            return '\n'.join((b.get('text') or '')
                             for b in pg['blocks'])
    return ''


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'dump':
        print(dump_case(sys.argv[2]))
    elif cmd == 'find':
        for h in find(sys.argv[2], sys.argv[3]):
            print(json.dumps(h, ensure_ascii=False))
