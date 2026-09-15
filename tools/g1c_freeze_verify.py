"""G1-C post-run freeze verification.

Re-verifica (sin tocar nada):
 - los 19 modulos del code-freeze (sha256 por fichero)
 - manifests de los 4 holdouts vs hashes del code-freeze
 - novelty-holdout, annotation-contract, development, freeze jsons
 - pyproject + requirements-lock
 - los 197 PDFs del universo vs document_sha256 de manifests
"""
import hashlib
import json
from pathlib import Path

CF = json.load(open('g1/manifests/code-freeze.json', encoding='utf-8'))


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


MOD_FILES = {
    'classification/dispatcher': 'src/emissions_es/classification/dispatcher.py',
    'extraction/dispatcher': 'src/emissions_es/extraction/dispatcher.py',
    'extraction/extractors': 'src/emissions_es/extraction/extractors.py',
    'extraction/normalize': 'src/emissions_es/extraction/normalize.py',
    'extraction/common': 'src/emissions_es/extraction/common/__init__.py',
    'extraction/final_terms': 'src/emissions_es/extraction/final_terms.py',
    'extraction/securities_note': 'src/emissions_es/extraction/securities_note.py',
    'extraction/issue_doc': 'src/emissions_es/extraction/issue_doc.py',
    'extraction/base_prospectus': 'src/emissions_es/extraction/base_prospectus.py',
    'linking/family_linker': 'src/emissions_es/linking/family_linker.py',
    'linking/rules': 'src/emissions_es/linking/rules.py',
    'linking/linker': 'src/emissions_es/linking/linker.py',
    'verification/verbatim': 'src/emissions_es/verification/verbatim.py',
    'terms/daycount': 'src/emissions_es/terms/daycount.py',
    'terms/exercise': 'src/emissions_es/terms/exercise.py',
    'terms/structured': 'src/emissions_es/terms/structured.py',
    'terms/coupon': 'src/emissions_es/terms/coupon.py',
    'lifecycle': 'src/emissions_es/lifecycle/__init__.py',
    'docview': 'src/emissions_es/extraction/docview.py',
}

MANIFESTS = {
    'family-map': 'g1/manifests/family-map.json',
    'novelty-holdout': 'g1/manifests/novelty-holdout.json',
    'annotation-contract': 'g1/manifests/annotation-contract.json',
    'g1-a1/development': 'g1/manifests/g1-a1/development.json',
    'g1-a1/extraction-holdout': 'g1/manifests/g1-a1/extraction-holdout.json',
    'g1-a1/linkage-holdout': 'g1/manifests/g1-a1/linkage-holdout.json',
    'g1-a1/lifecycle-holdout': 'g1/manifests/g1-a1/lifecycle-holdout.json',
}


def main():
    res = {'modules': {}, 'manifests': {}, 'locks': {}, 'pdfs': {}}
    ok = True
    for k, fp in MOD_FILES.items():
        good = Path(fp).exists() and sha(fp) == CF['modules'][k]
        res['modules'][k] = good
        ok &= good
    gm = CF['g1a1_freeze']['manifests']
    for k, fp in MANIFESTS.items():
        good = Path(fp).exists() and sha(fp) == gm[k]
        res['manifests'][k] = good
        ok &= good
    res['manifests']['g1-a1/freeze.json'] = \
        sha('g1/manifests/g1-a1/freeze.json') == \
        CF['g1a1_freeze']['freeze_json_sha256']
    res['manifests']['g1/manifests/freeze.json'] = \
        sha('g1/manifests/freeze.json') == \
        CF['g1a_initial_freeze_json_sha256']
    res['locks']['requirements-lock.txt'] = \
        sha('requirements-lock.txt') == CF['dependency_lock_sha256']
    res['locks']['pyproject.toml'] = \
        sha('pyproject.toml') == CF['pyproject_sha256']
    res['locks']['code-freeze.json'] = sha('g1/manifests/code-freeze.json')
    res['locks']['scoring-contract.json'] = \
        sha('g1/manifests/scoring-contract.json')
    ok &= all(res['manifests'].values()) and all(
        v is True or isinstance(v, str) for v in res['locks'].values())

    # PDFs del universo (los referenciados por los 4 manifests)
    seen = {}
    for mf in ('g1/manifests/g1-a1/extraction-holdout.json',
               'g1/manifests/g1-a1/linkage-holdout.json',
               'g1/manifests/g1-a1/lifecycle-holdout.json',
               'g1/manifests/novelty-holdout.json'):
        m = json.load(open(mf, encoding='utf-8'))
        docs = m.get('docs') or m.get('cases') or []
        for d in docs:
            p = d.get('local_evidence')
            s = d.get('document_sha256')
            if p and s:
                seen[p] = s
    bad, missing = [], []
    for p, s in seen.items():
        if not Path(p).exists():
            missing.append(p)
        elif sha(p) != s:
            bad.append(p)
    res['pdfs'] = {'n': len(seen), 'sha_fail': bad, 'missing': missing}
    ok &= not bad and not missing
    res['ALL_OK'] = ok
    print(json.dumps(res, indent=1))
    return res


if __name__ == '__main__':
    main()
