# -*- coding: utf-8 -*-
"""G0-C.1 hardening: runtime, environment lock, deep-dev freeze,
field-support, novelty map, prescan/decision, page provenance."""
import hashlib
import json
import platform
import re
import sys
from importlib.metadata import version as pkg_version
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------- runtime ----------

def test_python_runtime_consistency():
    """requires-python del pyproject == interprete que ejecuta los tests."""
    py = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    m = re.search(r'requires-python\s*=\s*"([^"]+)"', py)
    assert m, 'requires-python no declarado'
    spec = m.group(1)
    lo = re.search(r'>=\s*(\d+)\.(\d+)', spec)
    hi = re.search(r'<\s*(\d+)\.(\d+)', spec)
    vi = sys.version_info
    assert (vi.major, vi.minor) >= (int(lo.group(1)), int(lo.group(2)))
    if hi:
        assert (vi.major, vi.minor) < (int(hi.group(1)), int(hi.group(2)))
    assert platform.python_implementation() == 'CPython'


def test_environment_lock_integrity():
    lock = json.loads((ROOT / 'g0/environment-lock.json')
                      .read_text(encoding='utf-8'))
    assert lock['python']['version'] == platform.python_version()
    assert lock['python']['implementation'] == 'CPython'
    assert Path(lock['python']['executable']).resolve() == \
        Path(sys.executable).resolve()
    for pkg, v in lock['key_resolved_versions'].items():
        if v is not None:
            assert pkg_version(pkg) == v, f'{pkg}: lock={v} env={pkg_version(pkg)}'
    assert lock['lockfile']['sha256'] == _sha(ROOT / 'requirements-lock.txt')
    # environment_sha256 recomputable sobre el payload sin el campo
    doc = {k: v for k, v in lock.items() if k != 'environment_sha256'}
    payload = json.dumps(doc, ensure_ascii=False, sort_keys=True).encode()
    assert hashlib.sha256(payload).hexdigest() == lock['environment_sha256']


# ---------- deep-dev freeze ----------

def test_deep_dev_manifest_frozen():
    man = json.loads((ROOT / 'g0/manifests/extraction-deep-dev.json')
                     .read_text(encoding='utf-8'))
    cases = man['cases'] if isinstance(man, dict) else man
    assert 8 <= len(cases) <= 15
    required = {'case_key', 'issuer', 'document_role', 'instrument_class',
                'source_url', 'selection_reason', 'target_field_families'}
    for c in cases:
        assert required <= set(c), c['case_key']
        dl = c.get('downloaded') or {}
        assert dl.get('sha256') or c.get('document_sha256'), \
            f"{c['case_key']}: sin sha256 de documento"
    keys = {c['case_key'] for c in cases}
    assert len(keys) == len(cases), 'case_key duplicado'
    # disjunto con scout y holdout (solo claves, sin leer contenido)
    for other in ('extraction-scout', 'extraction-holdout'):
        o = json.loads((ROOT / f'g0/manifests/{other}.json')
                       .read_text(encoding='utf-8'))
        oc = o['cases'] if isinstance(o, dict) and 'cases' in o else o
        okeys = {x.get('case_key') or x.get('doc_key') for x in oc}
        assert not keys & okeys, f'solape con {other}'


# ---------- field support ----------

def test_field_support_integrity():
    from emissions_es.extraction.extractors import FIELD_SPECS
    fs = json.loads((ROOT / 'g0/manifests/field-support-freeze.json')
                    .read_text(encoding='utf-8'))
    fields = fs['fields']
    valid = {'SUPPORTED', 'PARTIAL', 'UNSUPPORTED_G0', 'NO_DEV_EVIDENCE'}
    for spec in FIELD_SPECS:
        assert spec.field in fields, f'{spec.field} no clasificado'
        f = fields[spec.field]
        assert f['status'] in valid
        assert f['extractor_version'] == spec.ver
        if f['status'] in ('SUPPORTED', 'PARTIAL'):
            assert f['supported_document_roles']
    # NO_DEV_EVIDENCE no puede pasar a SUPPORTED post-holdout
    assert 'no puede' in fs['rule']


# ---------- novelty map ----------

def test_novelty_map_integrity():
    from emissions_es.extraction.extractors import FIELD_SPECS
    nm = json.loads((ROOT / 'g0/manifests/novelty-field-map.json')
                    .read_text(encoding='utf-8'))
    valid = set(nm['states'])
    assert 'document_lineage' in nm['fields']
    for spec in FIELD_SPECS:
        assert spec.field in nm['fields'], f'{spec.field} sin novelty'
        f = nm['fields'][spec.field]
        for src in ('firds', 'esap', 'cnmv_structured'):
            assert f[src] in valid, (spec.field, src, f[src])


# ---------- prescan / selective decision ----------

def test_selective_decision_artifact():
    d = json.loads((ROOT / 'g0/results/docling-selective-decision.json')
                   .read_text(encoding='utf-8'))
    assert d['decision'] in ('KEEP_FULL', 'ADOPT_SELECTIVE')
    assert d['page_provenance']['verified'] is True
    if d['decision'] == 'KEEP_FULL':
        assert d['rationale']
    if d['decision'] == 'ADOPT_SELECTIVE':
        # si se adoptara, la paridad factual debe ser total
        assert d.get('factual_parity') is True


def test_prescan_covers_all_evidence_pages():
    cov = json.loads((ROOT / '.work/prescan-evidence-coverage.json')
                     .read_text(encoding='utf-8'))
    assert cov, 'sin documentos evaluados'
    for doc, rec in cov.items():
        assert rec['uncovered_evidence'] == [], \
            f'{doc}: evidencia fuera del prescan {rec["uncovered_evidence"]}'


def test_prescan_finds_anchor_pages():
    from prescan_pages import scan, to_ranges
    hits, total = scan(str(ROOT / 'g0/snapshots/Y01_CCFF_11400_043.pdf'))
    assert total > 1
    assert hits, 'prescan no encontro anclas en una CCFF conocida'
    ranges = to_ranges(hits, total=total)
    assert ranges and ranges[0][0] >= 1


# ---------- page provenance (conversion real, 1 pagina) ----------

def test_page_range_preserves_original_page_numbers():
    """Docling page_range no renumera: page_no = pagina original."""
    from docling.document_converter import DocumentConverter
    pdf = ROOT / 'g0/snapshots/Y01_CCFF_11400_043.pdf'
    if not pdf.exists():
        pytest.skip('snapshot no disponible')
    r = DocumentConverter().convert(str(pdf), page_range=(3, 3))
    pages = {p.page_no for it in r.document.texts for p in it.prov}
    assert pages and pages <= {3}, pages
