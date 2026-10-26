#!/usr/bin/env python3
"""Independent source/algebra auditor. Does not import build.py or its oracle."""
import argparse
import collections
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import pathlib

EXPECTED = {
 "SP.POP.TOTL": ("persons", "quantity"),
 "NY.GDP.MKTP.CD": ("current_USD", "quantity"),
 "NY.GDP.PCAP.CD": ("current_USD_per_person", "quantity"),
 "NY.GDP.MKTP.KD.ZG": ("percent_annual_GDP_growth", "rate"),
 "SP.DYN.LE00.IN": ("years", "quantity"),
 "EG.ELC.ACCS.ZS": ("percent_population_electricity", "rate"),
 "FP.CPI.TOTL.ZG": ("percent_annual_CPI_inflation", "rate"),
 "SP.URB.TOTL.IN.ZS": ("percent_population_urban", "rate"),
}


def normalized_decimal(value, round_derived=False):
    value = Decimal(value)
    if round_derived:
        value = value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    if value.is_zero():
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def evaluate(operator, rows):
    """A separate algebra implementation over model-visible rows only."""
    assert rows and len({r["cell_id"] for r in rows}) == len(rows), "empty/repeated evidence cells"
    if operator == "incompatible_sum":
        assert len(rows) == 2 and rows[0]["unit_code"] != rows[1]["unit_code"], "compatible sum mislabeled"
        return dict(status="incompatible_units", value=None, unit=None)
    unit = rows[0]["unit_code"]
    if operator == "lookup":
        assert len(rows) == 1
        return dict(status="missing" if rows[0]["value"] is None else "ok", value=rows[0]["value"], unit=unit)
    assert all(r["value"] is not None for r in rows), "non-lookup task uses missing source value"
    amounts = [Decimal(r["value"]) for r in rows]
    if operator == "gdp_per_capita_join":
        assert len(rows) == 2
        assert rows[0]["indicator_code"] == "NY.GDP.MKTP.CD" and rows[1]["indicator_code"] == "SP.POP.TOTL"
        assert rows[0]["year"] == rows[1]["year"] and rows[0]["economy_code"] == rows[1]["economy_code"]
        assert amounts[1] > 0
        return dict(status="ok", value=normalized_decimal(amounts[0] / amounts[1], True), unit="current_USD_per_person_calculated")
    assert len({r["indicator_code"] for r in rows}) == 1, "unrelated indicators compared"
    if operator in ("maximum_years", "minimum_years", "second_highest_years"):
        assert len({r["economy_code"] for r in rows}) == 1
        assert len({r["year"] for r in rows}) == len(rows)
        distinct = sorted(set(amounts))
        if operator == "minimum_years":
            chosen = distinct[0]
        elif operator == "maximum_years":
            chosen = distinct[-1]
        else:
            assert len(distinct) >= 2
            chosen = distinct[-2]
        years = sorted(row["year"] for row, value in zip(rows, amounts) if value == chosen)
        return dict(status="ok", value=years, unit="year")
    assert len(rows) == 2 and rows[0]["unit_code"] == rows[1]["unit_code"]
    if operator == "greater_than":
        assert rows[0]["economy_code"] == rows[1]["economy_code"] or rows[0]["year"] == rows[1]["year"]
        return dict(status="ok", value=amounts[0] > amounts[1], unit="boolean")
    assert rows[0]["economy_code"] == rows[1]["economy_code"]
    assert int(rows[0]["year"]) < int(rows[1]["year"])
    if operator == "difference":
        assert rows[0]["measure_kind"] == "quantity"
        result, output_unit = amounts[1] - amounts[0], unit
    elif operator == "percentage_point_difference":
        assert rows[0]["measure_kind"] == "rate"
        result, output_unit = amounts[1] - amounts[0], "percentage_points"
    elif operator == "relative_change":
        assert rows[0]["measure_kind"] == "quantity" and amounts[0] > 0
        result, output_unit = Decimal(100) * (amounts[1] / amounts[0] - Decimal(1)), "percent_change"
    else:
        raise AssertionError("Unknown operator: " + operator)
    return dict(status="ok", value=normalized_decimal(result, True), unit=output_unit)


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def audit(release, raw=None):
    release = pathlib.Path(release)
    raw = pathlib.Path(raw) if raw else release / "raw"
    manifest = json.loads((raw / "manifest.json").read_text())
    assert set(manifest["series"]) == set(EXPECTED)
    for entry in manifest["files"]:
        assert hashlib.sha256((raw / entry["file"]).read_bytes()).hexdigest() == entry["sha256"], "raw digest mismatch"
    source = {}
    for code in EXPECTED:
        meta = json.loads((raw / f"{code}.metadata.json").read_text())
        fields = {m["id"]: m["value"] for m in meta["source"][0]["concept"][0]["variable"][0]["metatype"]}
        assert fields["License_Type"] == "CC BY-4.0" and fields["License_URL"] == "https://datacatalog.worldbank.org/public-licenses#cc-by"
        assert fields["Source"] and fields["Unitofmeasure"]
        path = raw / f"{code}.observations.json"
        snapshot_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        header, rows = json.loads(path.read_text(), parse_float=Decimal)
        assert str(header["sourceid"]) == "2" and header["pages"] == 1 and header["total"] == len(rows)
        assert len(rows) == 550
        for row in rows:
            source[(row["countryiso3code"], code, row["date"])] = (row, snapshot_sha)
    observation_rows, questions, tables = [], [], []
    for split in ("train", "validation", "test"):
        for config, target in [("observations", observation_rows), ("questions", questions), ("tables", tables)]:
            rows = read_lines(release / "jsonl" / config / f"{split}.jsonl")
            assert all(row["split"] == split for row in rows)
            target.extend(rows)
            import pyarrow.parquet as pq
            loaded = pq.read_table(release / "data" / config / f"{split}-00000-of-00001.parquet").to_pylist()
            assert loaded == rows, "Parquet differs from corresponding JSONL"
    assert len(observation_rows) == len(source) == 4400
    assert len({x["cell_id"] for x in observation_rows}) == len(observation_rows)
    observed = {x["cell_id"]: x for x in observation_rows}
    economy_splits = collections.defaultdict(set)
    source_keys = set()
    for row in observation_rows:
        key = (row["economy_code"], row["indicator_code"], row["year"])
        assert key not in source_keys
        source_keys.add(key)
        upstream, sha = source[key]
        expected_value = None if upstream["value"] is None else normalized_decimal(upstream["value"])
        assert row["value"] == expected_value and row["source_snapshot_sha256"] == sha
        expected_id = "c_" + hashlib.sha256(json.dumps(["2", key[1], key[0], key[2], sha], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24]
        assert row["cell_id"] == expected_id
        assert row["economy_ar"] == upstream["country"]["value"] and row["source_obs_status"] == upstream["obs_status"]
        assert (row["unit_code"], row["measure_kind"]) == EXPECTED[row["indicator_code"]]
        economy_splits[row["economy_code"]].add(row["split"])
    assert all(len(value) == 1 for value in economy_splits.values()), "economy crosses splits"
    table_map = {row["table_id"]: row for row in tables}
    assert len(table_map) == len(tables)
    assert len({q["id"] for q in questions}) == len(questions)
    fingerprints, family_splits, used_cells = set(), collections.defaultdict(set), collections.defaultdict(set)
    visible_keys = {"cell_id", "economy_code", "economy_ar", "indicator_code", "indicator_ar", "year", "value", "unit_code", "unit_ar", "measure_kind"}
    operations = collections.Counter()
    for q in questions:
        assert "gold" not in q["context"] and "program" not in q["context"]
        context = json.loads(q["context"])
        assert set(context) == {"caption_ar", "source", "cells"}
        table = table_map[q["table_id"]]
        assert table["context"] == q["context"] and table["split"] == q["split"]
        for cell in context["cells"]:
            assert set(cell) == visible_keys
            assert cell == {key: observed[cell["cell_id"]][key] for key in visible_keys}, "context differs from source observation"
            assert observed[cell["cell_id"]]["split"] == q["split"], "source cell crosses task splits"
            used_cells[cell["cell_id"]].add(q["split"])
        program = json.loads(q["program"])
        assert program["operator"] == q["operation"]
        assert program["derived_decimal_places"] == 6 and program["rounding"] == "ROUND_HALF_UP"
        assert program["cells"] == [r["cell_id"] for r in context["cells"]] == q["gold_evidence_ids"]
        answer = evaluate(q["operation"], context["cells"])
        assert json.loads(q["gold_answer"]) == answer, "independent answer mismatch: " + q["id"]
        if q["structure_holdout_diagnostic"]:
            assert q["split"] == "test" and q["operation"] == "second_highest_years"
        if q["operation"] == "second_highest_years":
            assert q["structure_holdout_diagnostic"]
        fingerprint = (q["context"], q["question_ar"])
        assert fingerprint not in fingerprints, "duplicate input"
        fingerprints.add(fingerprint)
        family_splits[q["family_id"]].add(q["split"])
        operations[q["operation"]] += 1
        from model_input import model_input
        allowed_input = model_input(q)
        assert set(allowed_input) == {"question_ar", "table"} and allowed_input["table"] == context
    assert all(len(x) == 1 for x in used_cells.values()) and all(len(x) == 1 for x in family_splits.values())
    return {"passed": True, "source_observations": len(source), "questions": len(questions), "tables": len(tables),
            "source_cells_used_in_questions": len(used_cells), "source_cell_split_overlap": 0,
            "economy_split_overlap": 0, "exact_duplicate_inputs": 0, "independent_answer_mismatches": 0,
            "parquet_jsonl_equal": True, "operations": dict(operations),
            "scope": "Software and source-contract verification only; no human linguistic/statistical review or learned-model accuracy claim."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=pathlib.Path, required=True)
    parser.add_argument("--raw", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    report = audit(args.release, args.raw)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
