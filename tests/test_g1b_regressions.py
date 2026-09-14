"""Regression tests G1-B: cada fallo G0 convertido primero en test.

Solo datos DEVELOPMENT (G0 frozen + fixtures sinteticos). Nunca se lee
ningun holdout G1.
"""
import re

import pytest

from emissions_es.terms.daycount import resolve_daycount, DAYCOUNT_CANONICAL
from emissions_es.classification.dispatcher import (SourceDocument, classify)
from emissions_es.linking.family_linker import (OpDecision, family_key_of,
                                                link)
from emissions_es.linking.rules import Candidate, KnowledgeBase, SourceRecord
from emissions_es.lifecycle import LifecycleRelation, infer_relation


# ---------- F1: S4 programme succession ----------

def test_succession_never_autolinked_by_temporal_proximity():
    """S4: mismo emisor, programa anterior, sin sucesion declarada ->
    REVIEW_REQUIRED, nunca AUTO_LINKED."""
    kb = KnowledgeBase(folletos=[{"registro_oficial": "10999",
                                  "emisor": "BANCO X, S.A.",
                                  "rol": "PROGRAMA RENTA FIJA",
                                  "fecha_registro": "01/01/2023",
                                  "version_suffix": None}])
    src = SourceRecord(family="cnmv_folletos_emision", record_key="FOL_11000",
                       registro_oficial="11000", rol="PROGRAMA RENTA FIJA",
                       emisor="BANCO X, S.A.", fecha="01/01/2024")
    cand = Candidate(type="folleto", registro_oficial="10999")
    out = link(src, cand, kb)
    assert out.decision == OpDecision.REVIEW_REQUIRED
    assert out.decision != OpDecision.AUTO_LINKED


def test_explicit_numfol_autolinks():
    """CCFF con NUMFOL explicito en fila -> AUTO_LINKED al base."""
    kb = KnowledgeBase(folletos=[{"registro_oficial": "11500",
                                  "emisor": "BANCO Y", "rol": "X",
                                  "fecha_registro": "01/01/2024",
                                  "version_suffix": None}])
    src = SourceRecord(family="cnmv_ccff", record_key="CCFF_11500_001",
                       registro_oficial="11500", numfol_link="11500")
    cand = Candidate(type="folleto", registro_oficial="11500",
                     version="base")
    out = link(src, cand, kb)
    assert out.decision == OpDecision.AUTO_LINKED
    assert out.relation == "DEFINES_TERMS_FOR"


def test_wrong_numfol_is_no_link():
    src = SourceRecord(family="cnmv_ccff", record_key="CCFF_11500_001",
                       registro_oficial="11500", numfol_link="11500")
    cand = Candidate(type="folleto", registro_oficial="11999")
    out = link(src, cand)
    assert out.decision == OpDecision.NO_LINK


# ---------- F2: role classification ----------

def test_ccff_surface_classifies_final_terms():
    rec = SourceDocument("CCFF_11500_001", "CNMV_CCFF",
                         registro_oficial="11500", numfol="11500")
    c = classify(rec)
    assert c.document_role == "FINAL_TERMS"
    assert c.scope_role == "INSTRUMENT_DEFINING"
    assert c.document_family_key == "PROG_11500"


def test_admission_surface_debt_is_securities_note():
    rec = SourceDocument("ADM_143999", "CNMV_ADMISSION",
                         registro_oficial="143999",
                         source_meta={"denominacion": "BONOS/OBLIG."})
    c = classify(rec)
    assert c.document_role == "SECURITIES_NOTE"
    assert c.instrument_class == "DEBT"
    assert c.document_family_key == "ISSUE_ADM_143999"


def test_admission_surface_equity_is_out_of_scope():
    rec = SourceDocument("ADM_143998", "CNMV_ADMISSION",
                         registro_oficial="143998",
                         source_meta={"denominacion": "ACCIONES ORDINARIAS"})
    c = classify(rec)
    assert c.document_role == "ISSUE_DOC"
    assert c.scope_role == "OUT_OF_SCOPE"


def test_mention_does_not_classify():
    """'condiciones finales' en una referencia no convierte el doc."""
    rec = SourceDocument("FOL_11501", "CNMV_FOLLETOS_EMISION",
                         registro_oficial="11501", numfol="11501",
                         head_text="... vease las condiciones finales "
                                   "aplicables ..." * 3)
    c = classify(rec)
    # title regex matchea mencion -> MEDIUM; pero si el meta no aporta rol,
    # la clasificacion no debe ser HIGH ni inventar scope fuerte
    assert c.confidence in ("MEDIUM", "LOW")


def test_suffix_k_is_supplement():
    rec = SourceDocument("FOL_11502.3", "CNMV_FOLLETOS_EMISION",
                         registro_oficial="11502.3", numfol="11502")
    c = classify(rec)
    assert c.document_role == "SUPPLEMENT"
    assert c.scope_role == "LIFECYCLE"


# ---------- F4: day count '1/1' contexto ----------

def test_one_one_requires_context():
    assert resolve_daycount("1/1") is None  # sin contexto -> no convencion
    m = resolve_daycount("1/1", "Day Count Fraction: 1/1")
    assert m is not None and m.canonical == "ONE_ONE"


def test_daycount_specificity():
    m = resolve_daycount("ACT/ACT ICMA")
    assert m is not None and m.canonical == "ACT_ACT_ICMA"
    m = resolve_daycount("30E/360 ISDA")
    assert m is not None and m.canonical == "A_30E_360_ISDA"


# ---------- F5: call/put ExerciseTerms ----------

def test_exercise_terms_model():
    from emissions_es.terms.exercise import ExerciseTerms, OptionSide
    et = ExerciseTerms(option_side=OptionSide.CALL)
    assert et.option_side == OptionSide.CALL
    assert et.exercise_dates is None  # nunca inventado


# ---------- F6: structured barriers ----------

def test_barrier_concepts_separated():
    from emissions_es.terms.structured import StructuredProductTerms
    t = StructuredProductTerms()
    assert hasattr(t, "autocall") and hasattr(t, "coupon") \
        and hasattr(t, "protection")
    # no existe un campo 'barrier' generico
    assert not hasattr(t, "barrier")


# ---------- lifecycle ----------

def test_lifecycle_supplement():
    e = infer_relation("11510.2", "SUPLEMENTO", "11510")
    assert e and e.relation == LifecycleRelation.SUPPLEMENTS


def test_lifecycle_modification():
    e = infer_relation("11510-1", "MODIFICACION", "11510")
    assert e and e.relation == LifecycleRelation.MODIFIES


def test_lifecycle_wrong_target():
    assert infer_relation("11510.2", "SUPLEMENTO", "99999") is None
