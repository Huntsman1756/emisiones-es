"""Comparador de reobservacion G0-B.

Clasifica pares de observaciones (prev, cur) como:
  UNCHANGED   raw_sha256 identico
  UPDATED     raw difiere; normalized_row_sha256 difiere tambien (cambio de fila)
  UPDATED_METADATA  raw difiere pero normalized_row_sha256 identico
  DISAPPEARED cur ausente / status != 200
  NEW         prev ausente

Demuestra el diseno sobre observaciones reales (.work/reobs*.json) y
fixtures sinteticos; no requiere cambios reales en la fuente.
"""
import json, hashlib, re
from pathlib import Path

W = Path('.work')


def normalize_rowset(html: bytes) -> bytes:
    """Filas <td> normalizadas (espacios colapsados), orden estable.
    Ignora ViewState/headers/banners: solo contenido de celdas."""
    txt = html.decode('utf-8', 'replace')
    cells = [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', c)).strip()
             for c in re.findall(r'<td[^>]*>(.*?)</td>', txt, re.S)]
    return '\n'.join(cells).encode('utf-8')


def obs(key, raw: bytes, status=200):
    return {'key': key, 'status': status,
            'raw_sha256': hashlib.sha256(raw).hexdigest(),
            'normalized_row_sha256': hashlib.sha256(normalize_rowset(raw)).hexdigest()}


def classify(prev, cur):
    if prev is None and cur is not None and cur['status'] == 200:
        return 'NEW'
    if prev is not None and (cur is None or cur.get('status') != 200):
        return 'DISAPPEARED'
    if prev['raw_sha256'] == cur['raw_sha256']:
        return 'UNCHANGED'
    if prev['normalized_row_sha256'] == cur['normalized_row_sha256']:
        return 'UPDATED_METADATA'
    return 'UPDATED'


if __name__ == '__main__':
    out = {'real_pairs': [], 'fixtures': []}

    # pares reales adquiridos 2 veces en esta fase
    # pasada 1 (re_) vs pasada 2 (re2_), misma URL, ~6 min de separacion;
    # ademas folleto_11434.html es una captura anterior de la misma URL
    pairs = [
        ('ccff_santander_p0', '.work/re_ccff_santander_p0.html',
         '.work/re2_ccff_santander_p0.html'),
        ('folleto_11434', '.work/re_folleto_11434.html',
         '.work/re2_folleto_11434.html'),
        ('folleto_11434_earlier', '.work/folleto_11434.html',
         '.work/re2_folleto_11434.html'),
        ('listadosim', '.work/re_listadosim.html', '.work/re2_listadosim.html'),
    ]
    for key, f1, f2 in pairs:
        p = obs(key, Path(f1).read_bytes())
        c = obs(key, Path(f2).read_bytes())
        out['real_pairs'].append({'key': key, 'classification': classify(p, c),
                                  'prev_sha': p['raw_sha256'][:16],
                                  'cur_sha': c['raw_sha256'][:16]})

    # fixtures sinteticos: mismo HTML base con mutaciones controladas
    base = Path('.work/re2_ccff_santander_p0.html').read_bytes()
    fix = {
        'fx_unchanged': (obs('f', base), obs('f', base)),
        'fx_updated_row': (obs('f', base), obs('f', base.replace(b'AIAF', b'MARF', 1))),
        'fx_updated_metadata': (obs('f', base),
                              obs('f', base.replace(b'<title>', b'<title>!'))),
        'fx_disappeared': (obs('f', base), {'key': 'f', 'status': 404,
                                          'raw_sha256': None,
                                          'normalized_row_sha256': None}),
        'fx_new': (None, obs('f', base)),
    }
    for name, (p, c) in fix.items():
        out['fixtures'].append({'fixture': name, 'classification': classify(p, c)})

    json.dump(out, open('g0/results/reobservation-results.json', 'w',
                        encoding='utf-8'), ensure_ascii=False, indent=1)
    for r in out['real_pairs'] + out['fixtures']:
        print(r)
