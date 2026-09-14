"""Provenance: contrato de evidencia y utilidades.

El tipo canonico vive en `emissions_es.model.EvidencePointer`. Este
paquete agrupa las funciones que materializan evidencia desde cada
familia de fuentes (hoy: Docling via `extraction.docview`).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from emissions_es.model import EvidencePointer


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def snapshot_pointer(source: str, record_key: str, snapshot_sha256: str,
                     source_url: str | None = None,
                     retrieved_at: str | None = None) -> EvidencePointer:
    """Evidencia de nivel-registro (HTML/snapshot), sin geometria."""
    return EvidencePointer(source=source, source_record_key=record_key,
                           source_url=source_url,
                           snapshot_sha256=snapshot_sha256,
                           retrieved_at=retrieved_at)
