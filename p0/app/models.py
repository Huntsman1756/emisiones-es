"""Product states and decision model (P0-B).

Invariant: CANDIDATE != CONFIRMED. Only a human action creates
CONFIRMED/REJECTED/CONFLICT. machine_candidate is never overwritten.
"""

STATES = ('OBSERVED_SOURCE', 'CANDIDATE', 'CONFIRMED', 'REJECTED',
          'CONFLICT', 'MISSING', 'NOT_APPLICABLE')

HUMAN_DECISIONS = ('CONFIRMED', 'REJECTED', 'CONFLICT', 'MISSING',
                   'NOT_APPLICABLE')

ORIGINS = ('MACHINE_CANDIDATE', 'MANUAL_DISCOVERY')

FIELD_FAMILIES = {
    'Identity': ['isin', 'issuer'],
    'Issuance': ['currency', 'issue_date', 'maturity', 'denomination',
                 'issued_amount', 'ranking', 'subordination'],
    'Coupon': ['coupon_type', 'coupon_rate', 'benchmark', 'spread',
               'payment_frequency', 'day_count', 'business_day_convention',
               'reset_fixing'],
    'Exercise': ['call_put_terms', 'redemption'],
    'Structured payoff': ['underlying', 'observation_schedule', 'autocall',
                          'coupon_barrier', 'protection_barrier', 'strike',
                          'participation', 'cap'],
    'Legal / settlement': ['settlement'],
}

# review-schema field id -> g1 extraction field name (schema uses
# composite ids; candidates keep their original field name)
SCHEMA_TO_EXTRACTOR = {
    'isin': ['isin'],
    'issuer': [],
    'currency': ['currency'],
    'issue_date': ['issue_date'],
    'maturity': ['maturity'],
    'denomination': ['denomination'],
    'issued_amount': ['issued_amount'],
    'coupon_type': ['coupon_type'],
    'coupon_rate': ['coupon_rate'],
    'benchmark': ['benchmark'],
    'spread': ['spread'],
    'payment_frequency': ['payment_frequency'],
    'day_count': ['day_count'],
    'business_day_convention': ['business_day_convention'],
    'reset_fixing': ['reset_dates', 'fixing_rules'],
    'call_put_terms': ['call_dates', 'put_dates'],
    'ranking': ['ranking'],
    'subordination': ['subordination'],
    'underlying': ['underlying'],
    'observation_schedule': ['observation_dates'],
    'autocall': ['autocall'],
    'coupon_barrier': ['barrier'],
    'protection_barrier': ['barrier'],
    'strike': ['strike'],
    'participation': ['participation'],
    'cap': ['cap'],
    'redemption': ['redemption_formula'],
    'settlement': ['settlement_type'],
}

GRAPH_ROLES = ('BASE_PROSPECTUS', 'FINAL_TERMS', 'SECURITIES_NOTE',
               'ISSUE_DOC', 'SUPPLEMENT', 'ADMISSION', 'CORRECTION')

EDGE_STATES = ('AUTO_LINKED', 'REVIEW_REQUIRED')

EVENT_TYPES = (
    'CASE_OPENED', 'CASE_PAUSED', 'CASE_RESUMED', 'CASE_SUBMITTED',
    'FOCUS_LOST', 'FOCUS_GAINED',
    'DOCUMENT_OPENED', 'GRAPH_EDGE_FOLLOWED', 'EVIDENCE_JUMP',
    'PDF_SEARCH', 'CANDIDATE_CONFIRMED', 'CANDIDATE_REJECTED',
    'CANDIDATE_CONFLICT', 'MANUAL_FIELD_ADDED', 'STATUS_CHANGED',
    'FIELD_DECISION', 'SUBMIT',
)


def field_family(field_id):
    for fam, fields in FIELD_FAMILIES.items():
        if field_id in fields:
            return fam
    return 'Other'
