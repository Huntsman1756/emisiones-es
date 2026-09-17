"""Repro tooling (tools/repro/) — hash-check vs PROVENANCE.json + import.

These files are byte-identical copies of the adapter used during the
frozen experiments; the test guards against accidental edits.
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REPRO = REPO / 'tools' / 'repro'


def test_files_match_provenance_hashes():
    prov = json.loads(
        (REPRO / 'PROVENANCE.json').read_text(encoding='utf-8'))
    for name, info in prov['files'].items():
        sha = hashlib.sha256((REPRO / name).read_bytes()).hexdigest()
        assert sha == info['sha256'], f'{name} sha256 mismatch'


def test_adapter_imports_and_builds_ir():
    sys.path.insert(0, str(REPRO))
    try:
        import adapter_docling  # noqa: F401
        import ir
        doc = ir.DocumentIR(document_id='t', pages=[])
        assert doc.document_id == 't'
    finally:
        sys.path.remove(str(REPRO))
