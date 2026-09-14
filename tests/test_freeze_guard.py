"""Freeze guard: los holdouts y los thresholds preregistrados no pueden
cambiar durante G0-C. Falla si cualquier fichero congelado difiere del
hash registrado en g0/freeze-hashes.json."""
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN = json.load(open(ROOT / 'g0/freeze-hashes.json'))['files']

# solo los artefactos de evaluacion/thresholds estan protegidos;
# los scouts si pueden regenerarse durante desarrollo
PROTECTED = [
    'g0/manifests/linkage-holdout.json',
    'g0/manifests/extraction-holdout.json',
    'g0/manifests/g0-manifest.json',
]


def test_holdout_manifests_byte_identical():
    for rel in PROTECTED:
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert got == FROZEN[rel]['file_sha256'], f'{rel} modificado'


def test_holdout_internal_manifest_hash():
    for rel in PROTECTED[:2]:
        d = json.load(open(ROOT / rel, encoding='utf-8'))
        assert d['manifest_sha256'] == FROZEN[rel]['manifest_sha256']
        assert d['n_cases'] == FROZEN[rel]['n_cases']


def test_thresholds_unchanged():
    d = json.load(open(ROOT / 'g0/manifests/g0-manifest.json', encoding='utf-8'))
    blob = json.dumps(d)
    # umbrales preregistrados del G0 original; no mover a posteriori
    for needle in ('98', '99', '95'):
        assert needle in blob  # presencia basica; el hash garantiza el resto
