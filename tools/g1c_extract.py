"""G1-C: predicciones de extraccion sobre los 97 docs del holdout.

Solo ejecuta la pipeline congelada y serializa predicciones completas.
NO scoring, NO lectura de truth. El artifact se sella con SHA256.

Salida: g1/results/extraction-predictions.json
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, 'src')
from docling_core.types.doc import DoclingDocument

from emissions_es.classification.dispatcher import SourceDocument, classify
from emissions_es.extraction.docview import NormalizedDocumentView
from emissions_es.extraction.dispatcher import extract_document, extractor_for

EH = 'g1/manifests/g1-a1/extraction-holdout.json'
UNI = 'g1/manifests/universe.json'
DL = Path('.work/docling-g1-holdout')
OUT = Path('g1/results/extraction-predictions.json')


def rec_to_sdoc(r):
    return SourceDocument(
        source_record_key=r["source_record_key"],
        acquisition_surface=r["acquisition_surface"],
        registro_oficial=r.get("registro_oficial"),
        numfol=r.get("numfol"), issuer_key=r.get("issuer_key") or r.get("issuer"),
        source_meta={"rol": r.get("denominacion"),
                     "denominacion": r.get("denominacion"),
                     "tipo_valor": r.get("tipo_valor_src")})


def dump_obs(o):
    if o is None:
        return None
    return o.model_dump(mode='json')


def main():
    man = json.load(open(EH, encoding='utf-8'))
    uni = {r['source_record_key']: r for r in
           json.load(open(UNI, encoding='utf-8'))['records']}
    docs_out = []
    t_all = time.time()
    for d in man['docs']:
        key = d['source_record_key']
        fp = DL / f'{key}.json'
        rec = {'doc': key, 'docling': fp.exists()}
        if not fp.exists():
            rec['note'] = 'NO_DOCLING_CACHE'
            docs_out.append(rec)
            continue
        r = uni.get(key, {'source_record_key': key,
                          'acquisition_surface': d.get('acquisition_surface')})
        t0 = time.time()
        doc = DoclingDocument.load_from_json(str(fp))
        view = NormalizedDocumentView(
            doc, r.get('acquisition_surface', 'cnmv'), key,
            d.get('document_sha256'))
        sdoc = rec_to_sdoc(r)
        sdoc.head_text = (view.text() or '')[:4000]
        cl = classify(sdoc)
        ex = extractor_for(cl)
        res = extract_document(view, cl)
        fields = {}
        for f, er in res.items():
            if f.startswith('_'):
                continue
            fields[f] = {
                'observation': dump_obs(er.observation),
                'failure': er.failure.value if er.failure else None,
                'failure_detail': er.failure_detail,
                'located_regions': er.located_regions}
        rec.update(
            classification={
                'document_role': cl.document_role,
                'scope_role': cl.scope_role,
                'instrument_class': cl.instrument_class,
                'document_family_key': cl.document_family_key,
                'signals': cl.signals,
                'confidence': cl.confidence},
            extractor=ex.family_id if ex else None,
            extraction_seconds=round(time.time() - t0, 2),
            fields=fields)
        docs_out.append(rec)
        print(key, cl.document_role, cl.scope_role, len(fields), flush=True)

    out = {
        'phase': 'G1-C extraction predictions (sealed pre-truth)',
        'code_freeze': 'a1da72a',
        'manifest': EH,
        'manifest_sha256': man.get('manifest_sha256'),
        'n_docs': len(docs_out),
        'total_seconds': round(time.time() - t_all, 2),
        'documents': docs_out}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(OUT, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('wrote', OUT, len(docs_out))


if __name__ == '__main__':
    main()
