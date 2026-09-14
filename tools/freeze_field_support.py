#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Genera g0/manifests/field-support-freeze.json.

Estado por campo calculado SOLO con evidencia DEVELOPMENT
(extraction-scout + extraction-deep-dev). Un campo NO_DEV_EVIDENCE no
esta soportado ni insoportado: simplemente no se observo en dev.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, 'src')
from emissions_es.extraction.extractors import FIELD_SPECS

ROOT = Path(__file__).resolve().parent.parent

# status por campo fijado a mano desde la evidencia development
# (extraction-scout-results.json + extraction-deep-dev-results.json)
STATUS = {
    'isin':            ('SUPPORTED', []),
    'currency':        ('SUPPORTED', []),
    'issue_date':      ('SUPPORTED', []),
    'maturity':        ('SUPPORTED', []),
    'denomination':    ('SUPPORTED', []),
    'issued_amount':   ('SUPPORTED', []),
    'coupon_type':     ('PARTIAL', [
        'conflictos legitimos frecuentes (regimen fijo->variable, '
        'multi-pierna); conserva todos los valores']),
    'coupon_rate':     ('SUPPORTED', []),
    'benchmark':       ('SUPPORTED', [
        'objeto identificable obligatorio; prosa de disclosure no '
        'promueve (regresion Y08 fijada)']),
    'spread':          ('SUPPORTED', [
        'requiere signo explicito o puntos basicos; cupon fijo '
        'bare-pct no promueve']),
    'payment_frequency': ('SUPPORTED', [
        'rango/condicional/multi -> RAW_ONLY o CONFLICT; nunca '
        'reduccion silenciosa a canonico']),
    'day_count':       ('PARTIAL', [
        'texto normalizado minimo; colas de label en lexemas '
        'conocidos (no falsifica valor)']),
    'call_dates':      ('SUPPORTED', [
        'texto no-fecha -> RAW_ONLY; NOT_APPLICABLE explicito '
        'conservado']),
    'business_day_convention': ('SUPPORTED', [
        'value_pattern: nombre de convencion es objeto autocontenido; '
        'puede vivir dentro del valor de otro campo']),
    'put_dates':       ('PARTIAL', [
        'solo evidencia Aplicable/NA en dev; ninguna fecha put '
        'observada']),
    'reset_dates':     ('SUPPORTED', []),
    'fixing_rules':    ('SUPPORTED', [
        'pagina Reuters + hora de fijacion capturadas como raw text']),
    'ranking':         ('SUPPORTED', []),
    'subordination':   ('SUPPORTED', []),
    'redemption_formula': ('SUPPORTED', [
        'multi-clausula legitima -> CONFLICT conservado']),
    'underlying':      ('SUPPORTED', []),
    'barrier':         ('SUPPORTED', [
        'niveles multiples -> CONFLICT; header-cell misread posible '
        'en layouts de columna']),
    'autocall':        ('SUPPORTED', []),
    'observation_dates': ('SUPPORTED', [
        'series de fechas -> CONFLICT con todas las fechas '
        'observadas']),
    'settlement_type': ('SUPPORTED', []),
    'participation':   ('NO_DEV_EVIDENCE', [
        'sin documento dev que exponga participation']),
    'cap':             ('NO_DEV_EVIDENCE', [
        'solo Not applicable en dev; sin cap real observado']),
    'strike':          ('NO_DEV_EVIDENCE', [
        'sin documento dev que exponga strike']),
}

INSTR_CLASS = {
    'ranking': ['subordinado', 'at1_t2'], 'subordination': ['subordinado', 'at1_t2'],
    'underlying': ['estructurado', 'cubierto'], 'barrier': ['estructurado'],
    'autocall': ['estructurado'], 'observation_dates': ['estructurado'],
    'strike': ['estructurado'], 'participation': ['estructurado'],
    'cap': ['estructurado'], 'reset_dates': ['subordinado', 'cubierto'],
    'benchmark': ['cubierto', 'estructurado', 'subordinado'],
    'spread': ['cubierto', 'subordinado'],
}

EVIDENCE_REQ = ('label_value en text items o celdas de tabla; '
                'page+bbox provenance; raw_lexeme conservado; '
                'RAW_ONLY cuando no hay valor canonico seguro')


def main():
    fields = {}
    for spec in FIELD_SPECS:
        status, lims = STATUS.get(spec.field, ('UNSUPPORTED_G0', []))
        fields[spec.field] = {
            'status': status,
            'supported_document_roles': list(spec.doc_roles),
            'supported_instrument_classes': INSTR_CLASS.get(
                spec.field, ['*']),
            'extractor_id': 'label_value_v1',
            'extractor_version': spec.ver,
            'normalizer': spec.normalizer,
            'strategy': ('value_pattern' if spec.value_rx
                         else spec.strategy),
            'evidence_requirements': EVIDENCE_REQ,
            'known_limitations': lims,
        }
    doc = {
        'manifest': 'field-support-freeze.json',
        'frozen_for': 'G0-D one-shot holdout evaluation',
        'rule': 'un campo UNSUPPORTED_G0/NO_DEV_EVIDENCE no puede '
                'pasar a SUPPORTED tras abrir holdout',
        'evidence_base': ['extraction-scout (11 docs)',
                          'extraction-deep-dev (13 docs)'],
        'fields': fields,
    }
    out = ROOT / 'g0/manifests/field-support-freeze.json'
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False),
                   encoding='utf-8')
    import hashlib
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    print('fields:', len(fields), 'sha:', sha[:16])
    for f, d in fields.items():
        print(f"  {f:<26} {d['status']}")


if __name__ == '__main__':
    main()
