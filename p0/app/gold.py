"""Gold adjudication store (P0-E).

ADJUDICATOR_C works only from source documents. Gold units reuse the
same evidence-pointer validation as the reviewer app (evidence.py) —
a CONFIRMED_VALUE without a valid pointer cannot be written.

Units are append-only in gold.jsonl; last unit per (case, field) wins
for truth-v1, earlier units remain as audit trail.
"""
import json
import time
from pathlib import Path

from . import evidence

REPO = Path(__file__).resolve().parents[2]
GOLD_DIR = REPO / 'p0' / 'results' / 'gold'
SCHEMA = json.load(open(REPO / 'p0' / 'manifests' / 'review-schema.json',
                        encoding='utf-8'))
GOLD_STATES = ('CONFIRMED_VALUE', 'CONFLICT', 'MISSING', 'NOT_APPLICABLE')
ADJUDICATOR = 'ADJUDICATOR_C'
CRITICAL = {f['id'] for f in SCHEMA['fields'] if f['critical']}
ALL_FIELDS = [f['id'] for f in SCHEMA['fields']]


class GoldError(Exception):
    pass


class GoldStore:
    def __init__(self, root=GOLD_DIR):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.units_path = self.root / 'gold.jsonl'
        self.cases_path = self.root / 'gold_cases.jsonl'

    def _append(self, path, obj):
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(obj, ensure_ascii=False) + '\n')

    def _read(self, path):
        if not path.exists():
            return []
        return [json.loads(l) for l in
                open(path, encoding='utf-8').read().splitlines()
                if l.strip()]

    def units_for(self, case_id):
        return [u for u in self._read(self.units_path)
                if u['case_id'] == case_id]

    def record_unit(self, case_id, field, gold_status, gold_value=None,
                    evidence_pointers=None, adjudication_note=None,
                    second_check=None, ts=None):
        if field not in ALL_FIELDS:
            raise GoldError(f'unknown field {field}')
        if gold_status not in GOLD_STATES:
            raise GoldError(f'not a gold status: {gold_status}')
        pointers = list(evidence_pointers or [])

        if gold_status == 'CONFIRMED_VALUE':
            if gold_value in (None, '', []):
                raise GoldError('CONFIRMED_VALUE requires a value')
            if not pointers:
                raise GoldError('CONFIRMED_VALUE requires evidence pointer')
        if gold_status == 'CONFLICT' and not pointers:
            raise GoldError('CONFLICT requires evidence of both readings')
        for p in pointers:
            status, detail = evidence.validate_pointer(p)
            if status != 'OK':
                raise GoldError(f'BROKEN_EVIDENCE: {detail}')

        critical_verified = False
        if field in CRITICAL:
            if not second_check or second_check.get('result') != 'PASS':
                raise GoldError(
                    f'critical field {field} requires second_check PASS')
            if second_check.get('method') == 'value_in_page' and \
                    gold_status == 'CONFIRMED_VALUE':
                ok = self._value_in_page(pointers, gold_value)
                if not ok:
                    raise GoldError(
                        'second_check value_in_page FAILED: value not '
                        'found in pointed page text')
            critical_verified = True

        unit = {
            'case_id': case_id, 'field': field,
            'gold_status': gold_status, 'gold_value': gold_value,
            'evidence_pointers': pointers,
            'adjudication_note': adjudication_note,
            'critical_verified': critical_verified,
            'second_check': second_check,
            'adjudicator': ADJUDICATOR,
            'created_at': ts if ts is not None else time.time(),
        }
        self._append(self.units_path, unit)
        return unit

    @staticmethod
    def _value_in_page(pointers, value):
        """Second check: the confirmed value's tokens appear in the
        pointed page's text (independent of the recorded excerpt)."""
        from . import cases
        vals = value if isinstance(value, list) else [value]
        tokens = set()
        for v in vals:
            tokens.update(evidence._norm(str(v)).split())
        tokens.discard('')
        for p in pointers:
            ir = cases.ir_for(p['doc_id'])
            if not ir:
                continue
            pages = {pg['page_no']: pg for pg in ir['pages']}
            pg = pages.get(p.get('page'))
            if not pg:
                continue
            text = evidence._norm(' '.join(
                (bl.get('text') or '') for bl in pg['blocks']))
            if all(t in text for t in tokens):
                return True
        return False

    def seal_case(self, case_id):
        """Consistency check for one case; appends to gold_cases.jsonl."""
        units = self.units_for(case_id)
        latest = {}
        for u in units:
            latest[u['field']] = u
        missing = [f for f in ALL_FIELDS if f not in latest]
        if missing:
            raise GoldError(f'{case_id}: fields without unit {missing}')
        uncrit = [f for f in CRITICAL
                  if not latest[f]['critical_verified']]
        if uncrit:
            raise GoldError(f'{case_id}: critical units not verified {uncrit}')
        rec = {'case_id': case_id, 'adjudicator': ADJUDICATOR,
               'n_units': len(units), 'fields': len(latest),
               'sealed_at': time.time()}
        self._append(self.cases_path, rec)
        return rec
