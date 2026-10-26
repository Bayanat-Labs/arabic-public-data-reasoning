#!/usr/bin/env python3
"""Strict prediction scorer; numeric normalization never treats booleans as 0/1."""
import argparse
import collections
from decimal import Decimal, InvalidOperation
import json
import pathlib


def value_equal(predicted, gold):
    if isinstance(gold, bool):
        return isinstance(predicted, bool) and predicted is gold
    if gold is None:
        return predicted is None
    if isinstance(gold, list):
        return isinstance(predicted, list) and predicted == gold and all(isinstance(x, str) for x in predicted)
    if isinstance(predicted, bool) or predicted is None or isinstance(predicted, (list, dict)):
        return False
    try:
        expected, actual = Decimal(gold), Decimal(str(predicted))
    except (InvalidOperation, ValueError, TypeError):
        return False
    return actual.is_finite() and expected.is_finite() and actual == expected


def score_records(questions, predictions):
    gold_ids = {q["id"] for q in questions}
    assert len(gold_ids) == len(questions), "Duplicate reference IDs"
    by_id = {}
    for prediction in predictions:
        assert isinstance(prediction, dict) and isinstance(prediction.get("id"), str), "Prediction requires a string id"
        assert prediction["id"] not in by_id, "Duplicate prediction ID: " + prediction["id"]
        assert prediction["id"] in gold_ids, "Unknown/out-of-scope prediction ID: " + prediction["id"]
        by_id[prediction["id"]] = prediction
    groups = collections.defaultdict(lambda: collections.Counter())
    for q in questions:
        p = by_id.get(q["id"])
        reference = json.loads(q["gold_answer"])
        a = p.get("answer", {}) if p else {}
        valid_schema = isinstance(a, dict) and set(a) == {"status", "value", "unit"}
        status_exact = valid_schema and a["status"] == reference["status"]
        unit_exact = valid_schema and a["unit"] == reference["unit"]
        numeric_exact = valid_schema and value_equal(a["value"], reference["value"])
        answer_exact = bool(status_exact and unit_exact and numeric_exact)
        evidence = p.get("evidence_ids", []) if p else []
        valid_evidence_schema = isinstance(evidence, list) and all(isinstance(x, str) for x in evidence)
        if not valid_evidence_schema:
            evidence = []
        refs = set(q["gold_evidence_ids"])
        chosen = set(evidence)
        duplicate_citations = len(chosen) != len(evidence)
        nonexistent = len(chosen - refs)
        hits = len(chosen & refs)
        strict_joint = answer_exact and valid_evidence_schema and not duplicate_citations and chosen == refs
        for key in ("all", "split:" + q["split"], "operation:" + q["operation"],
                    "structure_holdout_diagnostic" if q["structure_holdout_diagnostic"] else "shared_operators"):
            s = groups[key]
            s.update(rows=1, missing_predictions=int(p is None), invalid_answer_schema=int(not valid_schema),
                     status_exact=int(status_exact), value_exact=int(numeric_exact), unit_exact=int(unit_exact),
                     answer_exact=int(answer_exact), strict_joint=int(strict_joint),
                     invalid_citation_ids=nonexistent, duplicate_citation_rows=int(duplicate_citations),
                     evidence_true_positive=hits, evidence_predicted=len(chosen), evidence_reference=len(refs))
    result = {}
    for key, s in groups.items():
        row = dict(s)
        for metric in ("status_exact", "value_exact", "unit_exact", "answer_exact", "strict_joint"):
            row[metric + "_rate"] = s[metric] / s["rows"]
        row["evidence_micro_precision"] = s["evidence_true_positive"] / s["evidence_predicted"] if s["evidence_predicted"] else 0.0
        row["evidence_micro_recall"] = s["evidence_true_positive"] / s["evidence_reference"] if s["evidence_reference"] else 0.0
        result[key] = row
    return {"groups": result,
            "protocol": "Missing predictions are wrong. Duplicate/unknown/out-of-scope prediction IDs fail the submission. Nonfinite/ill-typed values fail exact match. Duplicate/nonexistent citations fail strict joint. Scores separate all, shared operators and test-only structure diagnostic.",
            "evidence_limitation": "Visible contexts contain only the cells used by the formal program; citing all visible cells meets the evidence target. These metrics do not establish selective retrieval or faithful internal reasoning."}


def reject_constant(value):
    raise ValueError("Nonstandard/nonfinite JSON constant: " + value)


def load_predictions(path):
    return [json.loads(line, parse_float=Decimal, parse_constant=reject_constant) for line in path.read_text().splitlines() if line]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=pathlib.Path, required=True)
    parser.add_argument("--predictions", type=pathlib.Path, required=True)
    parser.add_argument("--split", choices=["train", "validation", "test", "all"], default="test")
    parser.add_argument("--scope", choices=["all", "shared", "diagnostic"], default="all")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    splits = ("train", "validation", "test") if args.split == "all" else (args.split,)
    questions = [json.loads(line) for split in splits for line in (args.release / "jsonl" / "questions" / (split + ".jsonl")).read_text().splitlines() if line]
    if args.scope != "all":
        questions = [q for q in questions if q["structure_holdout_diagnostic"] == (args.scope == "diagnostic")]
    assert questions, "Selected scope is empty"
    result = score_records(questions, load_predictions(args.predictions))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
