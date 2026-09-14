"""G1-B development runner — SOLO datos DEVELOPMENT.

Fuentes permitidas:
  - G1 development pool (g1/manifests/g1-a1/development.json + universe)
  - G0 linkage scout + G0 linkage holdout (post-cierre G0 = development)
  - G0 extraction deep-dev truth + G0 extraction-holdout truth
    (presence-level; ahora development)
  - caches Docling de .work/docling y .work/docling-holdout (G0)

NUNCA lee g1/manifests/*holdout* ni .work/.../holdout de G1.

Salidas:
  g1/results/development-classification.json
  g1/results/development-linkage.json
  g1/results/development-extraction.json
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, 'src')
from docling_core.types.doc import DoclingDocument

from emissions_es.classification.dispatcher import SourceDocument, classify
from emissions_es.extraction.docview import NormalizedDocumentView
from emissions_es.extraction.dispatcher import extract_document, extractor_for
from emissions_es.linking.family_linker import OpDecision, link
from emissions_es.linking.rules import Candidate, KnowledgeBase, SourceRecord
from emissions_es.model import FactStatus

SURF = {"cnmv_ccff": "CNMV_CCFF", "cnmv_folletos_emision": "CNMV_FOLLETOS_EMISION",
        "cnmv_admision": "CNMV_ADMISSION", "cnmv_folleto_detail":
        "CNMV_FOLLETO_DETAIL", "portfolio_exchange": "PORTFOLIO_EXCHANGE"}


def rec_to_sdoc(r):
    return SourceDocument(
        source_record_key=r["source_record_key"],
        acquisition_surface=r["acquisition_surface"],
        registro_oficial=r.get("registro_oficial"),
        numfol=r.get("numfol"), issuer_key=r.get("issuer_key") or r.get("issuer"),
        source_meta={"rol": r.get("denominacion"),
                     "denominacion": r.get("denominacion"),
                     "tipo_valor": r.get("tipo_valor_src")})


def case_to_sdoc(c):
    return SourceDocument(
        source_record_key=c["source_record_key"],
        acquisition_surface=SURF.get(c["source_family"], c["source_family"]),
        registro_oficial=c.get("registro_oficial"),
        source_meta={"rol": None, "denominacion": None})


# ---------------- classification ----------------

def run_classification():
    uni = {r["source_record_key"]: r for r in
           json.load(open("g1/manifests/universe.json",
                          encoding="utf-8"))["records"]}
    dev = json.load(open("g1/manifests/g1-a1/development.json",
                         encoding="utf-8"))
    keys = [k for k in dev["new_pool_docs"] if k in uni]
    rows, conf = [], Counter()
    for k in keys:
        r = uni[k]
        cl = classify(rec_to_sdoc(r))
        expected = r["document_role"]
        ok = cl.document_role == expected
        conf[(expected, cl.document_role)] += 1
        rows.append({"key": k, "expected": expected, "predicted":
                     cl.document_role, "confidence": cl.confidence,
                     "ok": ok, "signals": cl.signals})
    n = len(rows)
    unknown = sum(1 for x in rows if x["predicted"] == "UNKNOWN")
    false_conf = [x for x in rows if not x["ok"]
                  and x["predicted"] != "UNKNOWN"]
    return {"n": n, "role_accuracy": round(sum(x["ok"] for x in rows) / n, 4),
            "unknown_rate": round(unknown / n, 4),
            "false_confident": len(false_conf),
            "false_confident_keys": [x["key"] for x in false_conf][:20],
            "confusion": {f"{a}->{b}": c for (a, b), c in
                          sorted(conf.items()) if a != b},
            "per_record": rows}


# ---------------- linkage ----------------

def mk_src(s, by_key):
    o = by_key.get(s["record_key"], {})
    return SourceRecord(
        family=s["family"], record_key=s["record_key"],
        registro_oficial=s.get("registro_oficial") or o.get("registro_oficial"),
        version_suffix=s.get("version_suffix") or o.get("version_suffix"),
        rol=s.get("rol") or o.get("rol"),
        isin=s.get("isin") or o.get("isin"),
        doc_url=s.get("doc_url") or o.get("doc_url"),
        numfol_link=s.get("numfol_link") or o.get("numfol_link"),
        emisor=s.get("emisor") or o.get("emisor"),
        fecha=s.get("fecha") or o.get("fecha"))


def run_linkage():
    obs = json.load(open(".work/observations.json", encoding="utf-8"))
    kb = KnowledgeBase(folletos=obs["folletos"], ccff=obs["ccff"],
                       admisiones=obs["admisiones"])
    by_key = {o["source_record_key"]: o
              for o in obs["folletos"] + obs["ccff"] + obs["admisiones"]}
    cases = []
    for f in ("g0/manifests/linkage-scout.json",
              "g0/manifests/linkage-holdout.json"):
        m = json.load(open(f, encoding="utf-8"))
        cases += [(f.split("/")[-1], c) for c in m["cases"]]

    rows = []
    for src_name, c in cases:
        src = mk_src(c["source"], by_key)
        cand = Candidate(type=c["candidate"].get("type", "unknown"),
                         registro_oficial=c["candidate"].get("registro_oficial"),
                         isin=c["candidate"].get("isin"),
                         doc_url=c["candidate"].get("doc_url"),
                         record_key=c["candidate"].get("record_key"),
                         rol=c["candidate"].get("rol"),
                         version=c["candidate"].get("version"))
        r = link(src, cand, kb)
        rows.append({"case": c["case_key"], "manifest": src_name,
                     "stratum": c.get("stratum"), "label": c["label"],
                     "decision": r.decision.value, "relation": r.relation,
                     "rule_id": r.rule_id,
                     "neg": r.negative_evidence[:2]})

    auto = [r for r in rows if r["decision"] == "AUTO_LINKED"]
    false_auto = [r for r in auto if r["label"] != "EXACT_LINK"]
    n_exact = sum(1 for r in rows if r["label"] == "EXACT_LINK")
    forced = [r for r in rows if r["label"] == "AMBIGUOUS"
              and r["decision"] == "AUTO_LINKED"]
    by_stratum = defaultdict(Counter)
    for r in rows:
        by_stratum[r["stratum"]][r["decision"]] += 1
    return {"n_cases": len(rows),
            "auto_link_precision": round(
                sum(1 for r in auto if r["label"] == "EXACT_LINK")
                / max(1, len(auto)), 4),
            "auto_link_coverage": round(len(auto) / max(1, n_exact), 4),
            "review_required_rate": round(
                sum(1 for r in rows if r["decision"] == "REVIEW_REQUIRED")
                / len(rows), 4),
            "false_auto_links": len(false_auto),
            "false_auto_keys": [r["case"] for r in false_auto],
            "forced_ambiguous_to_auto": len(forced),
            "label_x_decision": {f"{a}|{b}": n for (a, b), n in
                                 Counter((r["label"], r["decision"])
                                         for r in rows).items()},
            "by_stratum": {k: dict(v) for k, v in by_stratum.items()},
            "per_case": rows}


# ---------------- extraction ----------------

FIELD_MAP = {}   # truth field -> spec field (identico en G1)

def score_doc(view, sdoc, truth):
    sdoc.head_text = (view.text() or "")[:4000]
    cl = classify(sdoc)
    ex = extractor_for(cl)
    out = {}
    if ex is None:
        return {"role": cl.document_role, "scope": cl.scope_role,
                "extractor": None, "fields": {}}
    res = extract_document(view, cl)
    for field, er in res.items():
        if field.startswith("_"):
            continue
        out[field] = er
    return {"role": cl.document_role, "scope": cl.scope_role,
            "extractor": ex.family_id, "fields": out}


def _accepted(er):
    """Observacion que cuenta como extraida: verbatim-verificada, con
    valor normalizado o lexema crudo (raw_only). Nunca NA ni cross-ref."""
    o = er.observation if er else None
    if o is None or o.status not in (FactStatus.OBSERVED,
                                     FactStatus.DERIVED):
        return False
    if o.confidence_class in ("VALUE_UNVERIFIED", "cross_reference"):
        return False
    if o.value == "NOT_APPLICABLE":
        return False
    return o.value is not None or bool(o.raw_lexeme)


def run_extraction():
    sets = [
        ("deep-dev", "g0/manifests/extraction-deep-dev.json",
         "g0/manifests/extraction-deep-dev-truth.json",
         Path(".work/docling")),
        ("g0-extraction-holdout-as-dev",
         "g0/manifests/extraction-holdout.json",
         "g0/holdout-truth/extraction-holdout-truth.json",
         Path(".work/docling-holdout")),
    ]
    per_field = defaultdict(Counter)
    failures = Counter()
    provenance_bad, unverified, invented = [], [], []
    doc_rows = []
    # Erratas objetivas sobre truth DEVELOPMENT (el truth G0 queda congelado
    # en v1.1; ver g1/manifests/dev-truth-errata.json). Se aplican solo al
    # scoring dev, nunca a artifacts G0.
    errata = {}
    er_f = Path("g1/manifests/dev-truth-errata.json")
    if er_f.exists():
        for e in json.load(open(er_f, encoding="utf-8"))["errata"]:
            for f, chg in e["fields"].items():
                new = chg.split("->")[-1]
                errata.setdefault(e["case"], {})[f] = new
    for set_name, man_f, truth_f, dl_dir in sets:
        man = json.load(open(man_f, encoding="utf-8"))
        truth = json.load(open(truth_f, encoding="utf-8"))["cases"]
        for c in man["cases"]:
            ck = c["case_key"]
            t = truth.get(ck)
            if t is None:
                continue
            t = dict(t["truth"] if "truth" in t else t)
            t.update(errata.get(ck, {}))
            cand = sorted(dl_dir.glob(ck + "_*.json"))
            if not cand:
                doc_rows.append({"case": ck, "set": set_name,
                                 "note": "no docling cache"})
                continue
            doc = DoclingDocument.load_from_json(str(cand[0]))
            sha = (c.get("downloaded") or {}).get("sha256")
            view = NormalizedDocumentView(
                doc, c.get("source_family", "cnmv"),
                c["source_record_key"], sha)
            r = score_doc(view, case_to_sdoc(c), t)
            row = {"case": ck, "set": set_name, "role": r["role"],
                   "scope": r.get("scope"), "extractor": r["extractor"],
                   "fields": {}}
            if r.get("scope") == "LIFECYCLE":
                # supplements/corrections: documentos de lineage, no
                # fuente contractual en G1 -> fuera del scoring de campos
                row["note"] = "lifecycle-scope doc: no term extraction"
                doc_rows.append(row)
                continue
            for field, want in t.items():
                field = FIELD_MAP.get(field, field)
                er = r["fields"].get(field)
                got = _accepted(er) if er else False
                na = (er and er.observation is not None and
                      er.observation.value == "NOT_APPLICABLE")
                if er and er.observation is not None and \
                        er.observation.status in (FactStatus.OBSERVED,
                                                  FactStatus.DERIVED):
                    if er.observation.confidence_class == "VALUE_UNVERIFIED":
                        unverified.append(f"{ck}:{field}")
                    if not er.observation.evidence:
                        provenance_bad.append(f"{ck}:{field}")
                if want in ("NA",):
                    continue
                if want in ("PRESENT", "MULTI"):
                    if got:
                        per_field[field]["TP"] += 1
                        row["fields"][field] = "TP"
                    elif er and er.observation is not None and \
                            er.observation.status == FactStatus.CONFLICT:
                        per_field[field]["CONFLICT"] += 1
                        row["fields"][field] = "CONFLICT"
                    elif er and er.observation is not None and \
                            er.observation.confidence_class == \
                            "cross_reference":
                        per_field[field]["XREF"] += 1
                        row["fields"][field] = "XREF"
                    elif na:
                        per_field[field]["FN_na"] += 1
                        row["fields"][field] = "FN_na"
                    else:
                        per_field[field]["FN"] += 1
                        row["fields"][field] = "FN"
                        if er is not None and er.failure:
                            failures[f"{field}:{er.failure.value}"] += 1
                elif want == "ABSENT":
                    if got:
                        per_field[field]["FP"] += 1
                        invented.append(f"{ck}:{field}")
                        row["fields"][field] = "FP"
                    else:
                        per_field[field]["TN"] += 1
            doc_rows.append(row)

    summary = {}
    for f, ct in sorted(per_field.items()):
        tp, fp = ct["TP"], ct["FP"]
        fn = ct["FN"] + ct["FN_na"] + ct["CONFLICT"] + ct["XREF"]
        summary[f] = {
            "TP": tp, "FP": fp, "FN": fn, "TN": ct["TN"],
            "of_which_conflict": ct["CONFLICT"], "of_which_xref": ct["XREF"],
            "precision": round(tp / max(1, tp + fp), 4),
            "recall": round(tp / max(1, tp + fn), 4),
            "coverage": round((tp + fp) / max(1, tp + fp + fn), 4)}
    n_obs = sum(ct["TP"] + ct["FP"] for ct in per_field.values())
    return {"sets": [s[0] for s in sets],
            "n_docs_scored": len(doc_rows),
            "per_field": summary,
            "failure_taxonomy": dict(failures.most_common()),
            "provenance_violations": provenance_bad,
            "value_unverified": unverified,
            "invented_or_unexpected": invented,
            "provenance_rate": round(
                (n_obs - len(provenance_bad)) / max(1, n_obs), 4),
            "documents": doc_rows}


def main():
    print("== classification ==")
    cls = run_classification()
    Path("g1/results").mkdir(exist_ok=True)
    json.dump(cls, open("g1/results/development-classification.json", "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
    print({k: cls[k] for k in ("n", "role_accuracy", "unknown_rate",
                               "false_confident")})
    print("== linkage ==")
    lk = run_linkage()
    json.dump(lk, open("g1/results/development-linkage.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=1)
    print({k: lk[k] for k in ("n_cases", "auto_link_precision",
                              "auto_link_coverage", "review_required_rate",
                              "false_auto_links", "forced_ambiguous_to_auto")})
    print("== extraction ==")
    ex = run_extraction()
    json.dump(ex, open("g1/results/development-extraction.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=1)
    print("docs:", ex["n_docs_scored"],
          "| prov:", ex["provenance_rate"],
          "| invented:", len(ex["invented_or_unexpected"]),
          "| unverified:", len(ex["value_unverified"]))
    for f, s in ex["per_field"].items():
        if s["TP"] or s["FN"]:
            print(f"  {f:26} P={s['precision']:.2f} R={s['recall']:.2f} "
                  f"TP={s['TP']} FP={s['FP']} FN={s['FN']}")


if __name__ == "__main__":
    main()
