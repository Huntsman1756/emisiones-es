"""P0-F — one-shot product scoring.

BLIND IMPLEMENTATION CONTRACT: this scorer was written and tested against
protocol.json + review-schema.json + synthetic fixtures only. The real
paths are supplied at execution time via CLI; nothing here reads
p0/results/p0d/* or p0/results/gold_human/* by itself.

  python -m p0.score_p0 \
      --p0d p0/results/p0d --gold p0/results/gold_human \
      --manifests p0/manifests --candidates p0/candidates \
      --out p0/results/p0f

Scoring model (frozen before data was read):

Per (case, reviewer, schema field):
  gold CONFIRMED_VALUE:
    CONFIRMED + equal value   -> TP
    CONFIRMED + wrong value   -> FP_WRONG_VALUE (+FN; CRITICAL_ERROR if critical)
    other / undecided         -> FN
  gold CONFLICT:
    decision CONFLICT         -> CONFLICT_OK
    decision CONFIRMED        -> FP_CONFLICT_DENIED (+ CRITICAL_ERROR if critical)
    other / undecided         -> FN
  gold MISSING | NOT_APPLICABLE:
    decision CONFIRMED        -> FP_INVENTED (+ CRITICAL_ERROR if critical)
    decision MISSING/N_A/REJ  -> TN
    decision CONFLICT         -> INCORRECT_STATUS
    undecided                 -> TN (nothing asserted)

Value equality: NFKC + casefold + whitespace-normalized; numbers compared
numerically; lists as multisets (a correct element plus an extra wrong one
is NOT a match); dicts recursively. Latest decision per field wins
(append-only log semantics).

unsupported CONFIRMED = CONFIRMED with zero pointers or any pointer that
fails evidence.validate_pointer against the case's authorized documents.

Timing: per case, assisted_active_seconds / manual_active_seconds using
only reviews with timing_status == 'VALID'. <24 valid pairs -> INCONCLUSIVE.
Bootstrap: paired resampling of case ratios, percentile 95% CI on the
median, seed 20260917, B=10000 (frozen constants below).

Verdict: PASS iff TIME + QUALITY + SAFETY + EVIDENCE + FREEZE all pass.
No NEAR PASS / PASS WITH CAVEATS.

v2/v3 (objective defect fixes, see p0/results/p0f/scorer-v1-to-v2.md):
  - timing_status absent from sealed P0-D reviews.jsonl (field added to
    store.py after the seal) -> recomputed from sealed events using the
    frozen rule: CASE_PAUSED not resumed/submitted within 300s ->
    INVALID_TIMING (mirrors p0/app/store.py submission logic).
  - value_equal: mechanical denotation equivalences only (ES/EN dates,
    ISO-4217 currency names, ES/EN number formats, %, punctuation-
    insensitive equality, containment with consistent numeric content).
    NO translation/synonymy: residual representation gaps count as
    disagreements and are reported as such.
"""
import hashlib
import json
import math
import random
import re
import statistics
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SCORER_VERSION = 3

# frozen before any real data was loaded (P0-F contract §3)
BOOTSTRAP_SEED = 20260917
BOOTSTRAP_REPLICATES = 10000
MIN_VALID_PAIRS = 24

HOLDOUT_STATUSES = ('CONFIRMED_VALUE', 'CONFLICT', 'MISSING', 'NOT_APPLICABLE')
# outcomes counted as false positives in confirmed-observation precision
FP_OUTCOMES = ('FP_WRONG_VALUE', 'FP_INVENTED', 'FP_CONFLICT_DENIED')
CRITICAL_ERROR_OUTCOMES = FP_OUTCOMES


# ---------- io ----------

def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha256_json(obj):
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    for i, line in enumerate(
            path.read_text(encoding='utf-8').splitlines(), 1):
        if line.strip():
            rows.append(json.loads(line))
    return rows


# ---------- value normalization ----------

def _norm_text(s):
    return ' '.join(unicodedata.normalize('NFKC', str(s)).casefold().split())


def _as_number(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(float(v)) else None
    if isinstance(v, str):
        t = v.strip().replace(',', '.')
        try:
            return float(t)
        except ValueError:
            return None
    return None


_MONTHS = {m: i for i, m in enumerate((
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
    'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'), 1)}
_MONTHS.update({m: i for i, m in enumerate((
    'january', 'february', 'march', 'april', 'may', 'june', 'july',
    'august', 'september', 'october', 'november', 'december'), 1)})

_CURRENCY = {}
for _code, _names in (
        ('eur', ('euro', 'euros', 'eur')),
        ('usd', ('dolar', 'dolares', 'dolar estadounidense', 'dollar',
                 'dollars', 'us dollar', 'usd',
                 'dólar', 'dólares', 'dólar estadounidense',
                 'dólares estadounidenses')),
        ('gbp', ('libra', 'libras', 'libra esterlina', 'pound',
                 'pounds', 'pound sterling', 'gbp')),
        ('chf', ('franco', 'francos', 'franco suizo', 'swiss franc', 'chf')),
        ('jpy', ('yen', 'yenes', 'jpy'))):
    for _n in _names:
        _CURRENCY[_n] = _code


def _to_date(s):
    """Parse ES/EN date forms -> (y, m, d) or None."""
    s = _norm_text(s)
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})\b', s)
    if m:
        return (int(m[1]), int(m[2]), int(m[3]))
    m = re.match(r'^(\d{1,2}) de ([a-z]+) de (\d{4})\b', s)
    if m and m[2] in _MONTHS:
        return (int(m[3]), _MONTHS[m[2]], int(m[1]))
    m = re.match(r'^(\d{1,2}) ([a-z]+) (\d{4})\b', s) or \
        re.match(r'^([a-z]+) (\d{1,2}),? (\d{4})\b', s)
    if m:
        mon = m[2] if m[2] in _MONTHS else m[1]
        if mon in _MONTHS:
            day = m[1] if m[2] in _MONTHS else m[2]
            return (int(m[3]), _MONTHS[mon], int(day))
    m = re.match(r'^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b', s)
    if m:
        return (int(m[3]), int(m[2]), int(m[1]))
    return None


def _numbers(s):
    """Numeric tokens with ES/EN separators normalized to float."""
    out = []
    for tok in re.findall(r'\d[\d.,]*', str(s)):
        t = tok.rstrip('.,')
        if not t:
            continue
        if '.' in t and ',' in t:  # last separator is the decimal mark
            if t.rfind('.') > t.rfind(','):
                t = t.replace(',', '')
            else:
                t = t.replace('.', '').replace(',', '.')
        elif ',' in t:
            t = t.replace(',', '') if re.fullmatch(
                r'\d{1,3}(,\d{3})+', t) else t.replace(',', '.')
        elif re.fullmatch(r'\d{1,3}(\.\d{3})+', t):
            t = t.replace('.', '')
        try:
            out.append(float(t))
        except ValueError:
            pass
    return out


def _alnum(s):
    return re.sub(r'[^a-z0-9]', '', _norm_text(s))


def _canon_text(s):
    """Normalized text with numeric tokens rewritten canonically and
    currency names mapped to ISO-4217."""
    s = _norm_text(s)
    for name, code in _CURRENCY.items():
        s = re.sub(rf'\b{re.escape(name)}\b', code, s)
    def _rep(m):
        t = m[0].rstrip('.,')
        vals = _numbers(t)
        return f'#{vals[0]:g}#' if len(vals) == 1 else m[0]
    return re.sub(r'\d[\d.,]*', _rep, s)


def _scalar_equal(a, b):
    """Mechanical denotation equivalence. No translation/synonymy."""
    na, nb = _as_number(a), _as_number(b)
    if na is not None and nb is not None:
        return na == nb
    sa, sb = _norm_text(a), _norm_text(b)
    if sa == sb:
        return True
    da, db = _to_date(a), _to_date(b)
    if da and db:
        return da == db
    if sa in _CURRENCY and sb in _CURRENCY:
        return _CURRENCY[sa] == _CURRENCY[sb]
    if _alnum(a) == _alnum(b) and _alnum(a):
        return True  # 'ACT/ACT (ICMA)' == 'ACT_ACT_ICMA'
    ca, cb = _canon_text(a), _canon_text(b)
    if ca == cb:
        return True  # '50.000 euros' == '50,000 EUR'
    # containment with consistent numeric content:
    # '4.35%' inside '4.35% of the initial nominal investment, ...'
    if ca and cb and (ca in cb or cb in ca):
        return _numbers(a) == _numbers(b)
    return False


def value_equal(a, b):
    """Normalized equality. Multi-values are multisets: correct element +
    extra wrong element does NOT count as a match."""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False
        return all(value_equal(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
        if not isinstance(a, (list, tuple)) or not isinstance(b, (list, tuple)):
            return False
        if len(a) != len(b):
            return False
        remaining = list(b)
        for x in a:
            hit = next((i for i, y in enumerate(remaining)
                        if value_equal(x, y)), None)
            if hit is None:
                return False
            remaining.pop(hit)
        return True
    return _scalar_equal(a, b)


# ---------- per-field classification ----------

def classify_unit(gold_status, gold_value, decision, critical):
    """decision: reviewer decision record or None (undecided).
    Returns outcome class string."""
    dec = (decision or {}).get('decision')
    val = (decision or {}).get('value')
    if gold_status == 'CONFIRMED_VALUE':
        if dec == 'CONFIRMED':
            return 'TP' if value_equal(val, gold_value) else 'FP_WRONG_VALUE'
        return 'FN'
    if gold_status == 'CONFLICT':
        if dec == 'CONFLICT':
            return 'CONFLICT_OK'
        if dec == 'CONFIRMED':
            return 'FP_CONFLICT_DENIED'
        return 'FN'
    # gold MISSING / NOT_APPLICABLE
    if dec == 'CONFIRMED':
        return 'FP_INVENTED'
    if dec == 'CONFLICT':
        return 'INCORRECT_STATUS'
    return 'TN'


def is_critical_error(outcome, critical):
    """CRITICAL_ERROR = error that materially changes the economic
    interpretation of a critical field: asserting a wrong/invented/
    conflict-denying value on a critical field."""
    return critical and outcome in CRITICAL_ERROR_OUTCOMES


# ---------- confusion / metrics ----------

def prf(outcomes):
    tp = outcomes.count('TP')
    fp = sum(outcomes.count(o) for o in FP_OUTCOMES)
    fn = outcomes.count('FN') + outcomes.count('FP_WRONG_VALUE')
    correct = (tp + outcomes.count('TN') + outcomes.count('CONFLICT_OK'))
    total = len(outcomes)
    return {
        'TP': tp, 'FP': fp, 'FN': fn,
        'precision': tp / (tp + fp) if tp + fp else None,
        'recall': tp / (tp + fn) if tp + fn else None,
        'completeness': correct / total if total else None,
        'n': total,
    }


def median(xs):
    xs = sorted(xs)
    return statistics.median(xs) if xs else None


def bootstrap_median_ci(ratios, seed=BOOTSTRAP_SEED, n=BOOTSTRAP_REPLICATES):
    """Paired resampling of case ratios; percentile 95% CI of the median.
    Deterministic: fixed seed + replicate count."""
    rng = random.Random(seed)
    meds = []
    k = len(ratios)
    for _ in range(n):
        meds.append(statistics.median(
            ratios[rng.randrange(k)] for _ in range(k)))
    meds.sort()
    lo = meds[int(0.025 * n)]
    hi = meds[int(0.975 * n) - 1]
    return lo, hi


# ---------- evidence validation (injected for tests) ----------

def default_pointer_validator(pointer, allowed_docs):
    from p0.app import evidence as _ev
    return _ev.validate_pointer(pointer, allowed_docs)


# ---------- case document authorization ----------

def case_authorized_docs(case, candidates):
    """Documents the reviewer may legitimately point at: case documents +
    observed graph nodes + candidate evidence docs (mirrors the app's
    case_documents authorization)."""
    docs = set(case.get('documents') or [])
    for n in (case.get('graph') or {}).get('nodes', []):
        if n.get('id'):
            docs.add(n['id'])
    for c in candidates or []:
        for p in c.get('evidence') or []:
            if p.get('doc_id'):
                docs.add(p['doc_id'])
    return docs


# ---------- core scoring ----------

def latest_decisions(decisions):
    """append-only log -> latest decision per field."""
    out = {}
    for d in decisions:
        out[d['field']] = d
    return out


def score_review(decisions, gold_fields, schema, allowed_docs,
                 pointer_validator=default_pointer_validator):
    """Score one review's decisions against gold. Returns per-field
    outcomes + evidence validation detail."""
    by_field = latest_decisions(decisions)
    critical_ids = {f['id'] for f in schema['fields'] if f['critical']}
    rows = []
    for f in schema['fields']:
        fid = f['id']
        gold = gold_fields.get(fid) or {}
        g_status = gold.get('gold_status')
        if g_status not in HOLDOUT_STATUSES:
            continue
        dec = by_field.get(fid)
        outcome = classify_unit(g_status, gold.get('gold_value'), dec,
                                fid in critical_ids)
        pointers = (dec or {}).get('evidence_pointers') or []
        ev_ok, ev_detail = True, []
        if dec is not None and dec.get('decision') == 'CONFIRMED':
            if not pointers:
                ev_ok = False
                ev_detail.append('CONFIRMED without evidence pointer')
            for p in pointers:
                status, detail = pointer_validator(p, allowed_docs)
                ev_detail.append({'pointer': p, 'status': status,
                                  'detail': detail})
                if status != 'OK':
                    ev_ok = False
        rows.append({'field': fid, 'critical': fid in critical_ids,
                     'gold_status': g_status, 'outcome': outcome,
                     'decision': (dec or {}).get('decision'),
                     'origin': (dec or {}).get('origin'),
                     'critical_error': is_critical_error(
                         outcome, fid in critical_ids),
                     'unsupported_confirmed': (
                         dec is not None
                         and dec.get('decision') == 'CONFIRMED'
                         and not ev_ok),
                     'evidence_valid': ev_ok,
                     'evidence_detail': ev_detail})
    return rows


def score_all(reviews, truth_cases, schema, cases_by_id,
              candidates_by_case, field_families,
              pointer_validator=default_pointer_validator):
    """reviews: list of {reviewer_id, case_id, mode, active_seconds,
    timing_status, decisions[], events[]}."""
    per_review, all_rows = [], []
    for r in reviews:
        gold_fields = (truth_cases.get(r['case_id']) or {}).get('fields', {})
        case = cases_by_id.get(r['case_id'], {})
        cands = candidates_by_case.get(r['case_id'], [])
        allowed = case_authorized_docs(case, cands)
        rows = score_review(r['decisions'], gold_fields, schema, allowed,
                            pointer_validator)
        # navigation events: evidence jumps pointing at docs
        nav_used = nav_ok = nav_wrongdoc = 0
        for e in r.get('events', []):
            if e.get('event_type') != 'EVIDENCE_JUMP':
                continue
            doc = (e.get('payload') or {}).get('doc_id')
            if not doc:
                continue
            nav_used += 1
            if doc in allowed:
                nav_ok += 1
            else:
                nav_wrongdoc += 1
        # decision evidence pointers count as evidence navigations
        for row in rows:
            for ed in row['evidence_detail']:
                nav_used += 1
                p = ed['pointer']
                if ed['status'] == 'OK':
                    nav_ok += 1
                if p.get('doc_id') not in allowed:
                    nav_wrongdoc += 1
        confirmed = sum(1 for row in rows if row['decision'] == 'CONFIRMED')
        minutes = (r['active_seconds'] or 0) / 60
        per_review.append({
            'reviewer_id': r['reviewer_id'], 'case_id': r['case_id'],
            'mode': r['mode'], 'active_seconds': r['active_seconds'],
            'timing_status': r['timing_status'],
            'rows': rows, 'confirmed': confirmed,
            'confirmed_per_minute': confirmed / minutes if minutes else None,
            'nav_used': nav_used, 'nav_ok': nav_ok,
            'nav_wrongdoc': nav_wrongdoc,
            'n_doc_opened': sum(1 for e in r.get('events', [])
                                if e.get('event_type') == 'DOCUMENT_OPENED'),
            'n_pdf_search': sum(1 for e in r.get('events', [])
                                if e.get('event_type') == 'PDF_SEARCH'),
            'n_evidence_jump': sum(1 for e in r.get('events', [])
                                   if e.get('event_type') == 'EVIDENCE_JUMP'),
            'n_manual_discovery': sum(
                1 for d in r['decisions']
                if d.get('origin') == 'MANUAL_DISCOVERY'),
            'n_cand_confirmed': sum(
                1 for d in r['decisions'] if d.get('origin') ==
                'MACHINE_CANDIDATE' and d.get('decision') == 'CONFIRMED'),
            'n_cand_rejected': sum(
                1 for d in r['decisions'] if d.get('origin') ==
                'MACHINE_CANDIDATE' and d.get('decision') == 'REJECTED'),
            'n_cand_conflict': sum(
                1 for d in r['decisions'] if d.get('origin') ==
                'MACHINE_CANDIDATE' and d.get('decision') == 'CONFLICT'),
        })
        all_rows.extend({**row, 'mode': r['mode'], 'case_id': r['case_id'],
                         'reviewer_id': r['reviewer_id']}
                        for row in rows)
    return per_review, all_rows


def _group(rows, key):
    out = {}
    for row in rows:
        out.setdefault(key(row), []).append(row['outcome'])
    return {k: prf(v) for k, v in sorted(out.items())}


def quality_scores(all_rows, strata, field_families):
    # FIELD_FAMILIES is {family: [field_ids]} -> reverse to {field: family}
    fam_of = {f: fam for fam, fields in field_families.items()
              for f in fields}
    by_mode = _group(all_rows, lambda r: r['mode'])
    by_stratum = _group(all_rows, lambda r: strata.get(r['case_id'], '?'))
    by_family = _group(all_rows, lambda r: fam_of.get(
        r['field'], 'Other'))
    by_crit = _group(all_rows, lambda r: 'critical' if r['critical']
                     else 'non_critical')
    return {'global': prf([r['outcome'] for r in all_rows]),
            'by_mode': by_mode, 'by_stratum': by_stratum,
            'by_field_family': by_family, 'by_criticality': by_crit}


def timing_status_from_events(events, submitted_at):
    """Recompute the frozen rule from sealed events: a CASE_PAUSED not
    followed by CASE_OPENED/CASE_RESUMED/CASE_SUBMITTED within 300 s
    invalidates timing. Mirrors p0/app/store.py submission logic
    (the sealed JSONL predates the timing_status field)."""
    events = sorted(events, key=lambda e: e['ts'])
    paused_at, invalid = None, False
    for ev in events:
        if ev['event_type'] == 'CASE_PAUSED' and paused_at is None:
            paused_at = ev['ts']
        elif ev['event_type'] in ('CASE_OPENED', 'CASE_RESUMED',
                                  'CASE_SUBMITTED') and paused_at is not None:
            invalid |= ev['ts'] - paused_at > 300
            paused_at = None
    if paused_at is not None:
        invalid |= (submitted_at or 0) - paused_at > 300
    return 'INVALID_TIMING' if invalid else 'VALID'


def timing_scores(per_review, mode_by_case):
    """Pair each case's MANUAL vs ASSISTED review."""
    pairs = []
    for cid, modes in mode_by_case.items():
        mr = next((r for r in per_review
                   if r['case_id'] == cid and r['mode'] == 'MANUAL'), None)
        ar = next((r for r in per_review
                   if r['case_id'] == cid and r['mode'] == 'ASSISTED'), None)
        valid = (mr and ar
                 and mr['timing_status'] == 'VALID'
                 and ar['timing_status'] == 'VALID'
                 and (mr['active_seconds'] or 0) > 0
                 and (ar['active_seconds'] or 0) > 0)
        pairs.append({'case_id': cid,
                      'manual_seconds': (mr or {}).get('active_seconds'),
                      'assisted_seconds': (ar or {}).get('active_seconds'),
                      'manual_reviewer': (mr or {}).get('reviewer_id'),
                      'assisted_reviewer': (ar or {}).get('reviewer_id'),
                      'manual_timing': (mr or {}).get('timing_status'),
                      'assisted_timing': (ar or {}).get('timing_status'),
                      'valid_pair': bool(valid)})
    ratios = [p['assisted_seconds'] / p['manual_seconds']
              for p in pairs if p['valid_pair']]
    out = {'pairs': pairs, 'n_pairs': len(pairs),
           'n_valid_pairs': len(ratios)}
    if ratios:
        med = median(ratios)
        lo, hi = bootstrap_median_ci(ratios)
        out.update({
            'ratios': ratios,
            'median_time_ratio': med,
            'median_time_reduction': 1 - med,
            'n_assisted_faster': sum(1 for r in ratios if r < 1),
            'pct_assisted_faster':
                sum(1 for r in ratios if r < 1) / len(ratios),
            'bootstrap': {'seed': BOOTSTRAP_SEED,
                          'replicates': BOOTSTRAP_REPLICATES,
                          'ci95': [lo, hi]},
        })
    return out


def safety_scores(all_rows):
    assisted = [r for r in all_rows if r['mode'] == 'ASSISTED']
    crit = [r for r in assisted if r['critical_error']]
    unsupported = [r for r in assisted if r['unsupported_confirmed']]
    conf = [r for r in assisted if r['decision'] == 'CONFIRMED']
    ev_ok = sum(1 for r in conf if r['evidence_valid'])
    return {'assisted_critical_errors': len(crit),
            'assisted_critical_error_detail': [
                {'case_id': r['case_id'], 'field': r['field'],
                 'outcome': r['outcome']} for r in crit],
            'assisted_unsupported_confirmed': len(unsupported),
            'assisted_confirmed': len(conf),
            'assisted_confirmed_with_valid_evidence': ev_ok,
            'assisted_evidence_rate':
                ev_ok / len(conf) if conf else None}


def evidence_scores(per_review):
    assisted = [r for r in per_review if r['mode'] == 'ASSISTED']
    used = sum(r['nav_used'] for r in assisted)
    ok = sum(r['nav_ok'] for r in assisted)
    wrong = sum(r['nav_wrongdoc'] for r in assisted)
    return {'evidence_navigations_used': used,
            'evidence_navigations_valid': ok,
            'navigation_rate': ok / used if used else None,
            'wrong_document_links': wrong}


def candidate_diagnostics(per_review, truth_cases, candidates_by_case,
                          schema_to_extractor):
    cand_dec = {'confirmed': 0, 'rejected': 0, 'conflict': 0}
    for r in per_review:
        cand_dec['confirmed'] += r['n_cand_confirmed']
        cand_dec['rejected'] += r['n_cand_rejected']
        cand_dec['conflict'] += r['n_cand_conflict']
    covered = total_gold = 0
    for cid, c in truth_cases.items():
        cands = candidates_by_case.get(cid, [])
        for fid, unit in c.get('fields', {}).items():
            if unit.get('gold_status') != 'CONFIRMED_VALUE':
                continue
            total_gold += 1
            efields = schema_to_extractor.get(fid, [])
            if any(c.get('field') in efields and
                   value_equal(c.get('value'), unit.get('gold_value'))
                   for c in cands):
                covered += 1
    return {**cand_dec,
            'candidate_decisions': sum(cand_dec.values()),
            'candidate_accept_rate': (cand_dec['confirmed'] /
                                      sum(cand_dec.values())
                                      if sum(cand_dec.values()) else None),
            'manual_discoveries': sum(r['n_manual_discovery']
                                      for r in per_review),
            'gold_confirmed_units': total_gold,
            'gold_covered_by_candidates': covered,
            'candidate_coverage_of_gold':
                covered / total_gold if total_gold else None,
            'docs_opened_per_review': mean_or_none(
                [r['n_doc_opened'] for r in per_review]),
            'pdf_searches_per_review': mean_or_none(
                [r['n_pdf_search'] for r in per_review]),
            'evidence_jumps_per_review': mean_or_none(
                [r['n_evidence_jump'] for r in per_review]),
            'confirmed_per_minute': mean_or_none(
                [r['confirmed_per_minute'] for r in per_review
                 if r['confirmed_per_minute'] is not None])}


def reviewer_diagnostics(per_review, truth_cases, schema):
    out = {}
    for r in per_review:
        d = out.setdefault(r['reviewer_id'], {
            'manual_seconds': [], 'assisted_seconds': [],
            'rows': []})
        d['manual_seconds' if r['mode'] == 'MANUAL'
          else 'assisted_seconds'].append(r['active_seconds'])
        d['rows'].extend(r['rows'])
    return {rid: {'manual_total_seconds': sum(d['manual_seconds']),
                  'assisted_total_seconds': sum(d['assisted_seconds']),
                  'quality': prf([x['outcome'] for x in d['rows']])}
            for rid, d in sorted(out.items())}


def mean_or_none(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


# ---------- gates / verdict ----------

def evaluate_gates(timing, quality, safety, evidence):
    gates = {}
    if timing['n_valid_pairs'] < MIN_VALID_PAIRS:
        gates['TIME'] = {'verdict': 'INCONCLUSIVE',
                         'reason': f"only {timing['n_valid_pairs']} "
                                   'valid paired timings'}
    else:
        g = [timing['median_time_ratio'] <= 0.60,
             timing['n_assisted_faster'] >= 21,
             timing['bootstrap']['ci95'][1] <= 0.80]
        gates['TIME'] = {'verdict': 'PASS' if all(g) else 'FAIL',
                         'checks': {'median<=0.60': g[0],
                                    '>=21/30 faster': g[1],
                                    'ci95 upper<=0.80': g[2]}}
    q = quality['by_mode']
    pa, pm = q.get('ASSISTED', {}), q.get('MANUAL', {})
    checks = {
        'assisted_precision>=0.99':
            pa.get('precision') is not None and pa['precision'] >= 0.99,
        'precision_noninferior':
            pa.get('precision') is not None and pm.get('precision') is not None
            and pa['precision'] >= pm['precision'] - 0.01,
        'recall_noninferior':
            pa.get('recall') is not None and pm.get('recall') is not None
            and pa['recall'] >= pm['recall'] - 0.05}
    gates['QUALITY'] = {'verdict': 'PASS' if all(checks.values()) else 'FAIL',
                        'checks': checks}
    checks = {'critical_errors==0':
                  safety.get('assisted_critical_errors') == 0,
              'unsupported_confirmed==0':
                  safety.get('assisted_unsupported_confirmed') == 0,
              'evidence_rate==1.0':
                  safety.get('assisted_evidence_rate') == 1.0}
    gates['SAFETY'] = {'verdict': 'PASS' if all(checks.values()) else 'FAIL',
                       'checks': checks}
    checks = {'navigation>=0.98': evidence.get('navigation_rate') is not None
              and evidence['navigation_rate'] >= 0.98,
              'wrong_document==0': evidence.get('wrong_document_links') == 0}
    gates['EVIDENCE'] = {'verdict': 'PASS' if all(checks.values()) else 'FAIL',
                         'checks': checks}
    return gates


def final_verdict(gates, freeze_ok):
    gates = dict(gates)
    gates['FREEZE'] = {'verdict': 'PASS' if freeze_ok else 'FAIL'}
    if gates['TIME']['verdict'] == 'INCONCLUSIVE':
        return 'INCONCLUSIVE', gates
    ok = all(g['verdict'] == 'PASS' for g in gates.values())
    return ('PASS' if ok else 'FAIL'), gates


# ---------- pipeline ----------

def load_inputs(p0d_dir, gold_dir, manifests_dir, candidates_dir):
    """Reads the real sealed artifacts. Called only at final execution."""
    manifests_dir = Path(manifests_dir)
    schema = json.loads((manifests_dir / 'review-schema.json')
                        .read_text(encoding='utf-8'))
    protocol = json.loads((manifests_dir / 'protocol.json')
                          .read_text(encoding='utf-8'))
    sample = json.loads((manifests_dir / 'sample.json')
                        .read_text(encoding='utf-8'))
    assignments = json.loads((manifests_dir / 'assignments.json')
                             .read_text(encoding='utf-8'))
    truth = json.loads((Path(gold_dir) / 'truth-human-v1.json')
                       .read_text(encoding='utf-8'))
    seal = json.loads((Path(gold_dir) / 'gold-human-seal.json')
                      .read_text(encoding='utf-8'))
    p0d_seal = json.loads((Path(p0d_dir) / 'p0d-seal.json')
                          .read_text(encoding='utf-8'))

    holdout = {c['case_id'] for c in sample['cases']}
    strata = {c['case_id']: c['stratum'] for c in sample['cases']}
    mode_by_case = {a['case_id']: {'REVIEWER_A': a['REVIEWER_A'],
                                  'REVIEWER_B': a['REVIEWER_B']}
                    for a in assignments['assignments']}
    case_meta = {c['case_id']: c for c in sample['cases']}
    cases_by_id = {}
    for c in sample['cases']:
        cases_by_id[c['case_id']] = {
            'documents': [c['source_record_key']],
            'graph': {'nodes': [{'id': c['source_record_key']}]}}
    candidates_by_case = {}
    for c in sample['cases']:
        cp = Path(candidates_dir) / f"{c['case_id']}.json"
        if cp.exists():
            obj = json.loads(cp.read_text(encoding='utf-8'))
            candidates_by_case[c['case_id']] = obj.get('candidates', [])
            g = obj.get('graph') or {}
            for n in g.get('nodes', []):
                if n.get('id') and n['id'] not in \
                        cases_by_id[c['case_id']]['documents']:
                    cases_by_id[c['case_id']]['graph']['nodes'].append(n)

    reviews = []
    for rid, info in p0d_seal['reviewers'].items():
        rdir = Path(p0d_dir) / Path(info['results_copy']).name
        decs = read_jsonl(rdir / 'decisions.jsonl')
        evs = read_jsonl(rdir / 'events.jsonl')
        revs = read_jsonl(rdir / 'reviews.jsonl')
        dec_by_case, ev_by_case = {}, {}
        for d in decs:
            dec_by_case.setdefault(d['case_id'], []).append(d)
        for e in evs:
            ev_by_case.setdefault(e['case_id'], []).append(e)
        for rev in revs:
            cid = rev['case_id']
            if cid not in holdout:
                continue  # warmup reviews never scored
            case_events = ev_by_case.get(cid, [])
            reviews.append({
                'reviewer_id': rid, 'case_id': cid,
                'mode': mode_by_case[cid][rid],
                'active_seconds': rev.get('active_seconds'),
                'timing_status': rev.get('timing_status')
                    or timing_status_from_events(
                        case_events, rev.get('submitted_at')),
                'decisions': dec_by_case.get(cid, []),
                'events': case_events})
    return {'schema': schema, 'protocol': protocol, 'sample': sample,
            'truth': truth, 'gold_seal': seal, 'p0d_seal': p0d_seal,
            'holdout': holdout, 'strata': strata,
            'mode_by_case': mode_by_case, 'case_meta': case_meta,
            'cases_by_id': cases_by_id,
            'candidates_by_case': candidates_by_case,
            'reviews': reviews}


def verify_seals(inputs, p0d_dir, expected_truth_sha=None):
    """Re-hash P0-D result files + human gold; compare vs seals."""
    problems = []
    for rid, info in inputs['p0d_seal']['reviewers'].items():
        rdir = Path(p0d_dir) / Path(info['results_copy']).name
        for name, sha in info['file_sha256'].items():
            actual = sha256_file(rdir / f'{name}.jsonl')
            if actual != sha:
                problems.append(f'{rid}/{name}: seal mismatch')
    tpath = sha256_json({k: v for k, v in inputs['truth'].items()
                         if k != 'truth_sha256'})
    if tpath != inputs['truth'].get('truth_sha256'):
        problems.append('truth sha mismatch')
    if inputs['gold_seal'].get('truth_sha256') != inputs['truth'].get(
            'truth_sha256'):
        problems.append('gold seal does not match truth')
    if expected_truth_sha and inputs['truth'].get('truth_sha256') != \
            expected_truth_sha:
        problems.append('truth sha != expected frozen sha')
    return problems


def run(p0d_dir, gold_dir, manifests_dir, candidates_dir, out_dir,
        expected_truth_sha=None):
    from p0.app.models import FIELD_FAMILIES, SCHEMA_TO_EXTRACTOR
    inputs = load_inputs(p0d_dir, gold_dir, manifests_dir, candidates_dir)
    problems = verify_seals(inputs, p0d_dir, expected_truth_sha)
    freeze_ok = not problems

    per_review, all_rows = score_all(
        inputs['reviews'], inputs['truth']['cases'], inputs['schema'],
        inputs['cases_by_id'], inputs['candidates_by_case'], FIELD_FAMILIES)
    timing = timing_scores(per_review, inputs['mode_by_case'])
    quality = quality_scores(all_rows, inputs['strata'], FIELD_FAMILIES)
    safety = safety_scores(all_rows)
    evidence = evidence_scores(per_review)
    cand = candidate_diagnostics(per_review, inputs['truth']['cases'],
                                 inputs['candidates_by_case'],
                                 SCHEMA_TO_EXTRACTOR)
    revd = reviewer_diagnostics(per_review, inputs['truth']['cases'],
                                inputs['schema'])
    gates = evaluate_gates(timing, quality, safety, evidence)
    verdict, gates = final_verdict(gates, freeze_ok)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    artifacts = {
        'timing-score.json': timing, 'quality-score.json': quality,
        'safety-score.json': safety, 'evidence-score.json': evidence,
        'candidate-diagnostics.json': cand,
        'reviewer-diagnostics.json': revd}
    final = {'artifact': 'p0-final-score', 'scorer_version': SCORER_VERSION,
             'verdict': verdict,
             'gates': gates, 'freeze_problems': problems,
             'truth_sha256': inputs['truth'].get('truth_sha256'),
             'scored_reviews': len(per_review),
             'scored_fields': len(all_rows),
             'created_at': datetime.now(timezone.utc).isoformat()}
    artifacts['p0-final-score.json'] = final
    for name, obj in artifacts.items():
        (out / name).write_text(json.dumps(obj, indent=1,
                                          ensure_ascii=False),
                               encoding='utf-8')
    seal = {'artifact': 'p0f-seal',
            'created_at': final['created_at'], 'verdict': verdict,
            'file_sha256': {n: sha256_file(out / n) for n in artifacts},
            'truth_sha256': final['truth_sha256'],
            'scorer_sha256': sha256_file(Path(__file__))}
    (out / 'p0f-seal.json').write_text(
        json.dumps(seal, indent=1, ensure_ascii=False), encoding='utf-8')
    return final, per_review, all_rows


def main():
    import argparse
    ap = argparse.ArgumentParser(description='P0-F one-shot scoring')
    ap.add_argument('--p0d', default='p0/results/p0d')
    ap.add_argument('--gold', default='p0/results/gold_human')
    ap.add_argument('--manifests', default='p0/manifests')
    ap.add_argument('--candidates', default='p0/candidates')
    ap.add_argument('--out', default='p0/results/p0f')
    ap.add_argument('--expect-truth-sha', default=None)
    args = ap.parse_args()
    final, _, _ = run(args.p0d, args.gold, args.manifests,
                      args.candidates, args.out, args.expect_truth_sha)
    print(f"P0 FINAL VERDICT: {final['verdict']}")
    for g, v in final['gates'].items():
        print(f"  {g}: {v['verdict']}")
    if final['freeze_problems']:
        print('  freeze problems:', final['freeze_problems'])


if __name__ == '__main__':
    main()
