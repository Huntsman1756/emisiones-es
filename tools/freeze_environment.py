"""G0-C.1: congela el entorno canonico en g0/environment-lock.json.

Ejecutar con el interprete del venv canonico (.venv, CPython 3.13):
    .venv/Scripts/python.exe tools/freeze_environment.py
"""
import hashlib
import json
import platform
import sys
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def v(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def main():
    lock = Path('requirements-lock.txt')
    direct = ['docling', 'pydantic', 'pypdf', 'pytest']
    resolved = {}
    if lock.exists():
        for line in lock.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '==' in line:
                n, _, ver = line.partition('==')
                resolved[n.strip()] = ver.strip()

    # opciones de pipeline observables: DocumentConverter() por defecto
    # = StandardPdfPipeline con PdfPipelineOptions por defecto
    pipeline = {}
    try:
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        o = PdfPipelineOptions()
        tso = getattr(o, 'table_structure_options', None)
        pipeline = {
            'converter': 'DocumentConverter()  # defaults',
            'pipeline_options': 'PdfPipelineOptions()  # defaults',
            'do_ocr': o.do_ocr,
            'ocr_kind': getattr(getattr(o, 'ocr_options', None),
                                'kind', None),
            'do_table_structure': o.do_table_structure,
            'table_mode': str(getattr(tso, 'mode', None)),
            'table_cell_matching': getattr(tso, 'do_cell_matching', None),
            'do_code_enrichment': getattr(o, 'do_code_enrichment', None),
            'do_formula_enrichment': getattr(o, 'do_formula_enrichment',
                                             None),
            'images_scale': getattr(o, 'images_scale', None),
            'generate_page_images': getattr(o, 'generate_page_images',
                                            None),
        }
    except Exception as e:
        pipeline['introspection_error'] = str(e)[:200]
    # modelos resueltos cuando son observables
    models = {}
    try:
        import docling_ibm_models
        models['docling_ibm_models'] = getattr(
            docling_ibm_models, '__version__', v('docling-ibm-models'))
    except Exception:
        models['docling_ibm_models'] = v('docling-ibm-models')
    pipeline['models'] = models

    doc = {
        'manifest': 'environment-lock.json',
        'purpose': 'runtime canonico reproducible para G0-D; el unico '
                   'interprete valido para la evaluacion one-shot',
        'python': {
            'version': platform.python_version(),
            'implementation': platform.python_implementation(),
            'platform': platform.platform(),
            'machine': platform.machine(),
            'executable': sys.executable,
        },
        'direct_dependencies': {d: v(d) for d in direct},
        'key_resolved_versions': {
            'docling': v('docling'),
            'docling-core': v('docling-core'),
            'docling-parse': v('docling-parse'),
            'docling-ibm-models': v('docling-ibm-models'),
            'docling-slim': v('docling-slim'),
            'pydantic': v('pydantic'),
            'pydantic-core': v('pydantic-core'),
            'pypdf': v('pypdf'),
            'pypdfium2': v('pypdfium2'),
            'torch': v('torch'),
            'rapidocr': v('rapidocr'),
        },
        'pipeline': pipeline,
        'lockfile': {
            'path': 'requirements-lock.txt',
            'sha256': sha256_file(lock) if lock.exists() else None,
            'n_resolved': len(resolved),
        },
        'install': 'uv pip install --python <py313> -r requirements-lock.txt',
    }
    payload = json.dumps(doc, ensure_ascii=False, sort_keys=True).encode()
    doc['environment_sha256'] = hashlib.sha256(payload).hexdigest()
    out = Path('g0/environment-lock.json')
    json.dump(doc, open(out, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(json.dumps({'python': doc['python']['version'],
                      'docling': doc['key_resolved_versions']['docling'],
                      'env_sha': doc['environment_sha256'][:16],
                      'lock_sha': doc['lockfile']['sha256'][:16],
                      'n_resolved': len(resolved)}, indent=1))


if __name__ == '__main__':
    main()
