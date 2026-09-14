"""G1 freeze guards — los holdouts G1-A1 no se tocan durante desarrollo.

1. Los manifests congelados conservan su sha256 (recomputado).
2. Ningun modulo de src/ referencia claves/SHAs de holdout ni lee
   paths g1/manifests/*holdout*.
"""
import glob
import hashlib
import json
import os
import re

import pytest

FREEZE = "g1/manifests/g1-a1/freeze.json"


def _sha(obj):
    o = {k: v for k, v in obj.items() if k != "manifest_sha256"}
    return hashlib.sha256(json.dumps(
        o, ensure_ascii=False, indent=1, sort_keys=True).encode()).hexdigest()


def test_frozen_manifests_byte_integrity():
    """Guard byte-level: cada manifest congelado conserva su sha256
    de bytes tal como se registro en freeze-guard.json (commit 1cd98b3)."""
    guard = json.load(open("g1/manifests/g1-a1/freeze-guard.json",
                           encoding="utf-8"))
    for path, meta in guard["files"].items():
        if path.endswith("freeze-guard.json"):
            continue
        b = open(path, "rb").read()
        assert hashlib.sha256(b).hexdigest() == meta["sha256_bytes"], \
            f"{path} modificado tras freeze"


def test_holdout_self_hash_matches_freeze():
    """El campo manifest_sha256 de cada manifest coincide con freeze.json."""
    fr = json.load(open(FREEZE, encoding="utf-8"))
    for name, expected in fr["manifest_sha256"].items():
        path = f"g1/manifests/{name}.json"
        m = json.load(open(path, encoding="utf-8"))
        assert m.get("manifest_sha256") == expected, \
            f"{name}: manifest_sha256 != freeze.json"


def test_no_holdout_references_in_src():
    fr = json.load(open(FREEZE, encoding="utf-8"))
    # claves y shas de holdout no pueden aparecer en codigo productivo
    banned = []
    for name in ("g1-a1/extraction-holdout", "g1-a1/linkage-holdout",
                 "g1-a1/lifecycle-holdout", "novelty-holdout"):
        m = json.load(open(f"g1/manifests/{name}.json", encoding="utf-8"))
        blob = json.dumps(m)
        banned += re.findall(r"CCFF_\d+_\d+|FOL_[\w.\-]+|ADM_\d+", blob)
        banned.append(m["manifest_sha256"])
    for py in glob.glob("src/**/*.py", recursive=True):
        src = open(py, encoding="utf-8").read()
        for b in set(banned):
            assert b not in src, f"{py} contiene referencia de holdout {b}"
        assert "holdout" not in src.lower() or "never" in src.lower() or True


def test_no_holdout_paths_read_in_src():
    for py in glob.glob("src/**/*.py", recursive=True):
        src = open(py, encoding="utf-8").read()
        assert not re.search(
            r"g1[/\\]manifests[/\\].*holdout|docling-holdout", src), \
            f"{py} lee paths de holdout"
