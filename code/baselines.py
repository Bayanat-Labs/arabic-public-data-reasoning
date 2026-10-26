#!/usr/bin/env python3
"""Honest input-only baselines. The symbolic baseline recognizes authored templates."""
import argparse
import collections
import json
import pathlib
from model_input import model_input
from verify import evaluate, read_lines


def symbolic(item):
    question, cells = item["question_ar"], item["table"]["cells"]
    if question.startswith("هل يمكن جمع"):
        op = "incompatible_sum"
    elif "اقسم إجمالي الناتج المحلي" in question:
        op = "gdp_per_capita_join"
    elif question.startswith("بعد ترتيب القيم المختلفة"):
        op = "second_highest_years"
    elif "القيمة الأعلى" in question:
        op = "maximum_years"
    elif "القيمة الأدنى" in question:
        op = "minimum_years"
    elif "نسبة التغير" in question:
        op = "relative_change"
    elif "التغير بالنقاط المئوية" in question:
        op = "percentage_point_difference"
    elif "الفرق بالوحدة المبينة" in question:
        op = "difference"
    elif "أكبر من" in question:
        op = "greater_than"
    elif "ما القيمة المسجلة" in question:
        op = "lookup"
    else:
        raise ValueError("Unsupported authored template")
    return evaluate(op, cells)


def first_cell(item):
    row = item["table"]["cells"][0]
    return {"status": "missing" if row["value"] is None else "ok", "value": row["value"], "unit": row["unit_code"]}


def run(release):
    questions = sum([read_lines(release / "jsonl" / "questions" / (split + ".jsonl")) for split in ("train", "validation", "test")], [])
    report = {"learned_model_evaluation": False,
              "scope": "Full released rows, using only model_input(question). The symbolic method recognizes every declared authored Arabic template and is a programmed format ceiling, not general Arabic understanding, training benefit or model performance.", "baselines": {}}
    for name, method in [("first_visible_cell", first_cell), ("template_aware_symbolic", symbolic)]:
        stats = collections.defaultdict(lambda: {"rows": 0, "exact_answer": 0, "status_exact": 0})
        predictions = []
        for q in questions:
            prediction = method(model_input(q))
            gold = json.loads(q["gold_answer"])
            for key in ("all", "split:" + q["split"], "operation:" + q["operation"], "diagnostic" if q["structure_holdout_diagnostic"] else "shared_operators"):
                stats[key]["rows"] += 1
                stats[key]["exact_answer"] += prediction == gold
                stats[key]["status_exact"] += prediction["status"] == gold["status"]
            evidence = [row["cell_id"] for row in model_input(q)["table"]["cells"]]
            predictions.append({"id": q["id"], "answer": prediction,
                                "evidence_ids": evidence if name == "template_aware_symbolic" else evidence[:1]})
        for item in stats.values():
            item["exact_answer_rate"] = item["exact_answer"] / item["rows"]
            item["status_exact_rate"] = item["status_exact"] / item["rows"]
        report["baselines"][name] = dict(stats)
        dest = release / "reports" / (name + ".predictions.jsonl")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in predictions))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=pathlib.Path, required=True)
    args = parser.parse_args()
    report = run(args.release)
    (args.release / "reports" / "baselines.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
