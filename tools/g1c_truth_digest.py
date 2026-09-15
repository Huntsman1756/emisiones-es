"""G1-C: digest de candidatos por campo para anotacion ciega de truth.

Ayuda de ANOTACION (no pipeline): lexemas amplios e independientes de
FIELD_SPECS. El anotador revisa estas lineas candidatas sobre el volcado
Docling y fija labels PRESENT/MULTI/NA/ABSENT + valores gold.

Salida: .work/g1c-truth-digest/<key>.txt (legible) + digest.json
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, 'src')
from docling_core.types.doc import DoclingDocument

DL = Path('.work/docling-g1-holdout')
OUT = Path('.work/g1c-truth-digest')
OUT.mkdir(parents=True, exist_ok=True)

PATTERNS = {
 'isin': r'\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b|C[oó]digo\s+ISIN|\bISIN\b',
 'currency': r'\bEUR\b|\bUSD\b|euros?|divisa|currency|denominad[oa]s?\s+en',
 'issue_date': r'[Ff]echa\s+de\s+[Ee]misi[oó]n|[Ii]ssue\s+[Dd]ate|fecha\s+de\s+disfrute|[Ff]echa\s+de\s+[Ee]xpedici[oó]n',
 'maturity': r'vencimiento|maturity|fecha\s+de\s+amortizaci[oó]n|redemption\s+date',
 'denomination': r'denominaci[oó]n|nominal\s+unitario|denomination|valor\s+nominal',
 'issued_amount': r'importe|aggregate|nominal\s+total|volumen|amount\s+of|efectivo\s+total',
 'coupon_type': r'tipo\s+de\s+inter[eé]s|fixed|floating|variable|cero\s+cup[oó]n|zero|indexad|cup[oó]n|rate\s+of\s+interest|tipo\s+fijo|tipo\s+variable',
 'coupon_rate': r'inter[eé]s\s+nominal|rate\s+of\s+interest|cup[oó]n\s+(?:fijo|variable|anual)|[0-9][,.]?[0-9]*\s*%',
 'benchmark': r'euribor|mibor|sonia|sofr|libor|estr|cms|mid-?swap|[ií]ndice\s+de\s+referencia|reference\s+rate|tipo\s+de\s+referencia',
 'spread': r'margen|spread|basis\s+points|puntos\s+b[aá]sicos|\bbps\b|margin',
 'payment_frequency': r'pago\s+de\s+intereses|interest\s+payment|anual(?:mente)?|semestral|trimestral|mensual|frequency|frecuencia|peri[oó]dic',
 'day_count': r'act/|30/360|/360|/365|base\s+de\s+c[aá]lculo|day\s*count|actual/|\b1/1\b|c[oó]mputo',
 'call_dates': r'call|amortizaci[oó]n\s+anticipada|early\s+redemption|reembolso\s+anticipado|opci[oó]n.{0,25}(emisor|compra)|opci[oó]n\s+del\s+emisor',
 'business_day_convention': r'd[ií]a\s+h[aá]bil|business\s+day|h[aá]biles|modified\s+following|following|preceding|ajuste',
 'put_dates': r'\bput\b|opci[oó]n\s+de\s+venta|opci[oó]n.{0,25}(inversor|tenedor)|reventa',
 'reset_dates': r'reset|revisi[oó]n|determinaci[oó]n\s+de\s+intereses|determination\s+date|fixing\s+date|fecha\s+de\s+determinaci[oó]n|fecha\s+de\s+revisi[oó]n',
 'fixing_rules': r'fixing|pantalla|screen|reuters|isda|publicaci[oó]n|reference\s+banks|bancos\s+de\s+referencia|tasa\s+de\s+referencia',
 'ranking': r'rango|ranking|pari\s+passu|senior|preferente|ordinaria|orden\s+de\s+prelaci[oó]n|jerarqu[ií]a',
 'subordination': r'subordinad|junior|tier|at1|at2|subordinated',
 'redemption_formula': r'amortizaci[oó]n|redemption|reembolso|importe\s+de\s+reembolso|f[oó]rmula|reimbursement',
 'underlying': r'subyacente|underlying|[ií]ndice\b|cesta|acci[oó]n|fondo',
 'barrier': r'barrera|barrier|nivel\s+de\s+(?:protecci[oó]n|barrera)|umbral|knock',
 'autocall': r'autocall|cancelable|vencimiento\s+anticipado|early\s+(?:termination|redemption)|callable|reembolso\s+anticipado',
 'observation_dates': r'observaci[oó]n|observation\s+date|valoraci[oó]n|valuation\s+date',
 'settlement_type': r'liquidaci[oó]n|settlement|entrega|delivery|entrega\s+f[ií]sica|cash\s+settlement',
 'participation': r'participaci[oó]n|participation',
 'cap': r'\bcap\b|techo|m[aá]ximo\s+del\s+cup[oó]n|l[ií]mite\s+superior',
 'strike': r'strike|ejercicio|precio\s+de\s+ejercicio|nivel\s+inicial|initial\s+level|precio\s+inicial',
}
RX = {f: re.compile(p, re.I) for f, p in PATTERNS.items()}


def page_of(item):
    prov = getattr(item, 'prov', None) or []
    return getattr(prov[0], 'page_no', None) if prov else None


def digest_doc(key, doc):
    hits = {f: [] for f in PATTERNS}
    for t in doc.texts:
        txt = (getattr(t, 'text', '') or '').strip()
        if not txt:
            continue
        pg = page_of(t)
        for f, rx in RX.items():
            if rx.search(txt) and len(hits[f]) < 10:
                hits[f].append({'p': pg, 't': txt[:220]})
    for tb in doc.tables:
        pg = page_of(tb)
        for row in tb.data.grid:
            cells = [(c.text or '').strip() for c in row]
            line = ' | '.join(c for c in cells if c)
            if not line:
                continue
            for f, rx in RX.items():
                if rx.search(line) and len(hits[f]) < 10:
                    hits[f].append({'p': pg, 'tbl': True, 't': line[:220]})
    return hits


def main():
    man = json.load(open('g1/manifests/g1-a1/extraction-holdout.json',
                         encoding='utf-8'))
    out = {}
    for d in man['docs']:
        key = d['source_record_key']
        fp = DL / f'{key}.json'
        if not fp.exists():
            out[key] = {'error': 'no docling'}
            continue
        doc = DoclingDocument.load_from_json(str(fp))
        out[key] = digest_doc(key, doc)
        lines = [f'== {key} ==']
        for f in PATTERNS:
            if out[key].get(f):
                lines.append(f'-- {f}')
                for h in out[key][f]:
                    lines.append(f"   p{h.get('p')} {'[T]' if h.get('tbl') else ''} {h['t']}")
        (OUT / f'{key}.txt').write_text('\n'.join(lines), encoding='utf-8')
        print(key, 'done', flush=True)
    json.dump(out, open(OUT / 'digest.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('docs:', len(out))


if __name__ == '__main__':
    main()
