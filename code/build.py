#!/usr/bin/env python3
"""Deterministic original QA tasks over frozen, real WDI observations."""
import argparse
import collections
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import pathlib
import shutil

from fetch import ECONOMIES, SERIES

UNITS = {
 "SP.POP.TOTL": ("persons", "نسمة", "quantity"),
 "NY.GDP.MKTP.CD": ("current_USD", "دولار أمريكي بالأسعار الجارية", "quantity"),
 "NY.GDP.PCAP.CD": ("current_USD_per_person", "دولار أمريكي بالأسعار الجارية للفرد", "quantity"),
 "NY.GDP.MKTP.KD.ZG": ("percent_annual_GDP_growth", "% سنوياً", "rate"),
 "SP.DYN.LE00.IN": ("years", "سنة", "quantity"),
 "EG.ELC.ACCS.ZS": ("percent_population_electricity", "% من السكان", "rate"),
 "FP.CPI.TOTL.ZG": ("percent_annual_CPI_inflation", "% سنوياً", "rate"),
 "SP.URB.TOTL.IN.ZS": ("percent_population_urban", "% من السكان", "rate"),
}


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def identifier(prefix, obj):
    return prefix + hashlib.sha256(canonical(obj).encode()).hexdigest()[:24]


def number(value, places=None):
    value = Decimal(str(value))
    if places is not None:
        value = value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    if value == 0:
        return "0"
    result = format(value, "f")
    return result.rstrip("0").rstrip(".") if "." in result else result


def read_json(path):
    return json.loads(path.read_text(), parse_float=Decimal)


def metadata(raw, series):
    obj = read_json(raw / f"{series}.metadata.json")
    fields = {m["id"]: m["value"] for m in obj["source"][0]["concept"][0]["variable"][0]["metatype"]}
    assert fields["License_Type"] == "CC BY-4.0", (series, fields.get("License_Type"))
    assert fields["License_URL"] == "https://datacatalog.worldbank.org/public-licenses#cc-by"
    a = read_json(raw / f"{series}.ar.json")[1][0]
    e = read_json(raw / f"{series}.en.json")[1][0]
    assert a["name"] and any("\u0600" <= c <= "\u06ff" for c in a["name"])
    return {"indicator_code": series, "label_ar": a["name"], "label_en": e["name"],
            "source_definition_ar_endpoint": a["sourceNote"], "source_definition_en": e["sourceNote"],
            "source_providers": fields["Source"], "source_unit": fields["Unitofmeasure"],
            "license": fields["License_Type"], "license_url": fields["License_URL"],
            "source_metadata_url": f"https://api.worldbank.org/v2/sources/2/series/{series}/metadata?format=json",
            "indicator_url": f"https://data.worldbank.org/indicator/{series}",
            "unit_code": UNITS[series][0], "unit_ar": UNITS[series][1], "measure_kind": UNITS[series][2]}


def splits():
    ordered = sorted(ECONOMIES, key=lambda code: hashlib.sha256(("bayanat-public-data-v0.1:" + code).encode()).hexdigest())
    return {code: "train" if i < 16 else "validation" if i < 19 else "test" for i, code in enumerate(ordered)}


def solve(program, cells):
    """Generation oracle. verify.py intentionally implements a separate interpreter."""
    refs = [cells[x] for x in program["cells"]]
    op = program["operator"]
    if op == "incompatible_sum":
        assert refs[0]["unit_code"] != refs[1]["unit_code"]
        return {"status": "incompatible_units", "value": None, "unit": None}
    unit = refs[0]["unit_code"]
    if op == "lookup":
        return {"status": "missing" if refs[0]["value"] is None else "ok", "value": refs[0]["value"], "unit": unit}
    if any(x["value"] is None for x in refs):
        return {"status": "missing", "value": None, "unit": unit}
    values = [Decimal(x["value"]) for x in refs]
    if op in ("maximum_years", "minimum_years", "second_highest_years"):
        unique = sorted(set(values), reverse=op != "minimum_years")
        selected = unique[1] if op == "second_highest_years" else unique[0]
        return {"status": "ok", "value": sorted(x["year"] for x in refs if Decimal(x["value"]) == selected), "unit": "year"}
    if op == "greater_than":
        return {"status": "ok", "value": values[0] > values[1], "unit": "boolean"}
    if op in ("difference", "percentage_point_difference"):
        value = values[1] - values[0]
        if op == "percentage_point_difference":
            unit = "percentage_points"
    elif op == "relative_change":
        assert values[0] > 0 and refs[0]["measure_kind"] == "quantity"
        value = (values[1] - values[0]) / values[0] * 100
        unit = "percent_change"
    elif op == "gdp_per_capita_join":
        assert refs[0]["indicator_code"] == "NY.GDP.MKTP.CD" and refs[1]["indicator_code"] == "SP.POP.TOTL"
        assert values[1] > 0
        value = values[0] / values[1]
        unit = "current_USD_per_person_calculated"
    else:
        raise ValueError(op)
    return {"status": "ok", "value": number(value, 6), "unit": unit}


def visible(row):
    keys = ["cell_id", "economy_code", "economy_ar", "indicator_code", "indicator_ar", "year", "value", "unit_code", "unit_ar", "measure_kind"]
    return {key: row[key] for key in keys}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical(row) + "\n" for row in rows))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=pathlib.Path, help="Fresh output directory for a deterministic rebuild")
    args = parser.parse_args()
    raw = args.project / "raw"
    release = args.output or args.project / "release"
    release.mkdir(parents=True, exist_ok=True)
    manifest = read_json(raw / "manifest.json")
    for entry in manifest["files"]:
        assert hashlib.sha256((raw / entry["file"]).read_bytes()).hexdigest() == entry["sha256"]
    split_map = splits()
    series_info = {code: metadata(raw, code) for code in SERIES}
    observations = []
    source_snapshots = {}
    for code in SERIES:
        path = raw / f"{code}.observations.json"
        blob = read_json(path)
        header, rows = blob
        assert header["pages"] == 1 and header["total"] == 550 and str(header["sourceid"]) == "2", header
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        source_snapshots[code] = {"sha256": sha, "api_lastupdated": header["lastupdated"], "rows": len(rows)}
        for row in rows:
            economy = row["countryiso3code"]
            assert economy in ECONOMIES and row["country"]["id"] == ECONOMIES[economy]
            info = series_info[code]
            cell = {"cell_id": identifier("c_", ["2", code, economy, row["date"], sha]),
                    "source_id": "2", "indicator_code": code, "indicator_ar": info["label_ar"],
                    "indicator_en": info["label_en"], "economy_code": economy,
                    "economy_iso2": row["country"]["id"], "economy_ar": row["country"]["value"],
                    "year": row["date"], "value": None if row["value"] is None else number(row["value"]),
                    "unit_code": info["unit_code"], "unit_ar": info["unit_ar"], "source_unit": info["source_unit"],
                    "measure_kind": info["measure_kind"], "source_obs_status": row["obs_status"],
                    "source_decimal_hint": row["decimal"], "source_snapshot_sha256": sha,
                    "source_api_lastupdated": header["lastupdated"], "split": split_map[economy]}
            observations.append(cell)
    observations.sort(key=lambda x: (x["economy_code"], x["indicator_code"], x["year"]))
    cells = {x["cell_id"]: x for x in observations}
    by_key = {(x["economy_code"], x["indicator_code"], int(x["year"])): x for x in observations}
    assert len(cells) == len(by_key) == len(observations)
    questions, tables, fingerprints = [], {}, set()

    def add(refs, op, question_ar, question_en, diagnostic=False):
        assert len(set(x["split"] for x in refs)) == 1
        context = {"caption_ar": "قيم مسجلة في لقطة مؤشرات التنمية العالمية؛ لا تعني المقارنة تطابق التعريفات الوطنية.",
                   "source": "World Bank: World Development Indicators (source 2)",
                   "cells": [visible(x) for x in refs]}
        table_id = identifier("t_", context)
        tables[table_id] = {"table_id": table_id, "split": refs[0]["split"], "context": canonical(context)}
        program = {"operator": op, "cells": [x["cell_id"] for x in refs], "derived_decimal_places": 6, "rounding": "ROUND_HALF_UP"}
        answer = solve(program, cells)
        fingerprint = canonical([context, question_ar])
        assert fingerprint not in fingerprints
        fingerprints.add(fingerprint)
        family_id = identifier("f_", [op, program["cells"]])
        questions.append({"id": identifier("q_", [family_id, question_ar]), "family_id": family_id,
                          "table_id": table_id, "split": refs[0]["split"], "question_ar": question_ar,
                          "question_en": question_en, "context": canonical(context),
                          "operation": op, "template_id": "v1_" + op,
                          "structure_holdout_diagnostic": diagnostic,
                          "gold_answer": canonical(answer), "gold_evidence_ids": [x["cell_id"] for x in refs],
                          "program": canonical(program), "annotation_method": "deterministic_template_and_Decimal_program",
                          "question_language_method": "Bayanat controlled Arabic and English, AI-assisted authorship; no human validation"})

    for economy in sorted(ECONOMIES):
        for code in SERIES:
            for start in range(2000, 2025, 5):
                refs = [by_key[economy, code, year] for year in range(start, start + 5)]
                valid = [x for x in refs if x["value"] is not None]
                missing = [x for x in refs if x["value"] is None]
                title = series_info[code]["label_ar"]
                country = refs[0]["economy_ar"]
                # One source-backed lookup per nonoverlapping five-year block, not one per cell.
                item = valid[-1] if valid else refs[-1]
                add([item], "lookup", f"بحسب الخلية المعروضة، ما القيمة المسجلة للمؤشر «{title}» في {country} عام {item['year']}؟",
                    f"According to the displayed cell, what is the recorded value of {series_info[code]['label_en']} in {economy} in {item['year']}?")
                if missing and valid:
                    item = missing[0]
                    add([item], "lookup", f"ما القيمة المسجلة للمؤشر «{title}» في {country} عام {item['year']}؟ إذا كانت الخلية خالية فأعد الحالة missing دون تخمين.",
                        f"What is the recorded value of {series_info[code]['label_en']} in {economy} in {item['year']}? Return status missing for an empty cell.")
                if len(valid) < 2:
                    continue
                first, last = valid[0], valid[-1]
                op = "percentage_point_difference" if UNITS[code][2] == "rate" else "difference"
                wording = "التغير بالنقاط المئوية" if op == "percentage_point_difference" else "الفرق بالوحدة المبينة"
                add([first, last], op,
                    f"احسب {wording} للمؤشر «{title}» في {country}: قيمة {last['year']} ناقص قيمة {first['year']}. قرب الناتج إلى ست منازل عشرية بطريقة النصف إلى الأعلى.",
                    f"For {code} in {economy}, calculate the {('percentage-point change' if op == 'percentage_point_difference' else 'difference in the displayed unit')}: {last['year']} minus {first['year']}. Round to six decimal places, half up.")
                add([first, last], "greater_than",
                    f"هل القيمة المسجلة للمؤشر «{title}» في {country} عام {first['year']} أكبر من القيمة المسجلة عام {last['year']}؟ أعد قيمة منطقية.",
                    f"Is the recorded value of {code} in {economy} in {first['year']} greater than in {last['year']}? Return a boolean.")
                if UNITS[code][2] == "quantity" and Decimal(first["value"]) > 0:
                    add([first, last], "relative_change",
                        f"للمؤشر «{title}» في {country}، احسب نسبة التغير بين {first['year']} و{last['year']} بالصيغة (القيمة اللاحقة − القيمة السابقة) ÷ القيمة السابقة × 100، إلى ست منازل عشرية بطريقة النصف إلى الأعلى. هذا تغير في القيم المعروضة فقط.",
                        f"For {code} in {economy}, compute ({last['year']} value minus {first['year']} value) / {first['year']} value * 100. Round to six decimals, half up; this is a change in displayed values only.")
                for operator, ar_word, en_word in [("maximum_years", "الأعلى", "highest"), ("minimum_years", "الأدنى", "lowest")]:
                    add(valid, operator, f"بين السنوات المعروضة فقط، ما السنوات التي سجلت القيمة {ar_word} للمؤشر «{title}» في {country}؟ أعد جميع سنوات التعادل مرتبة تصاعدياً.",
                        f"Among displayed years only, which years have the {en_word} recorded value of {code} in {economy}? Return every tied year in ascending order.")
                if split_map[economy] == "test" and len(set(x["value"] for x in valid)) >= 2:
                    add(valid, "second_highest_years",
                        f"بعد ترتيب القيم المختلفة المعروضة للمؤشر «{title}» في {country} تنازلياً، ما سنوات القيمة الثانية؟ أعد جميع سنوات هذه القيمة مرتبة تصاعدياً، مع تجاهل تكرار القيمة عند تحديد المرتبة.",
                        f"Sort distinct displayed {code} values for {economy} from highest to lowest. Return all years of the second distinct value, in ascending order.", True)
        for year in range(2000, 2025):
            gdp, pop = by_key[economy, "NY.GDP.MKTP.CD", year], by_key[economy, "SP.POP.TOTL", year]
            if gdp["value"] is not None and pop["value"] is not None and Decimal(pop["value"]) > 0:
                add([gdp, pop], "gdp_per_capita_join",
                    f"من الخليتين المعروضتين لعام {year} في {gdp['economy_ar']}، اقسم إجمالي الناتج المحلي بالدولار الجاري على إجمالي السكان. ما الناتج المحسوب بالدولار الجاري للفرد إلى ست منازل عشرية بطريقة النصف إلى الأعلى؟ لا تستخدم سلسلة نصيب الفرد المنشورة منفصلة.",
                    f"Using only the two displayed {year} cells for {economy}, divide current-US-dollar GDP by total population. Return calculated current USD per person, six decimals half up, rather than the separately published GDP-per-capita series.")
            life = by_key[economy, "SP.DYN.LE00.IN", year]
            if year % 5 == 0 and gdp["value"] is not None and life["value"] is not None:
                add([gdp, life], "incompatible_sum",
                    f"هل يمكن جمع قيمة إجمالي الناتج المحلي بالدولار الجاري وقيمة العمر المتوقع بالسنوات في {gdp['economy_ar']} عام {year} وإرجاع مجموع له وحدة واحدة؟ إذا اختلفت الوحدتان فأعد الحالة incompatible_units وقيمة فارغة.",
                    f"Can current-dollar GDP and life expectancy in years for {economy} in {year} be added to return a total with one unit? Return incompatible_units and a null value when units differ.")
    # Bounded neighboring-economy comparisons: deterministic pairs inside each split only.
    for split in ("train", "validation", "test"):
        cohort = sorted(c for c, s in split_map.items() if s == split)
        for left, right in zip(cohort, cohort[1:]):
            for code in SERIES:
                for year in (2000, 2005, 2010, 2015, 2020, 2024):
                    a, b = by_key[left, code, year], by_key[right, code, year]
                    if a["value"] is not None and b["value"] is not None:
                        add([a, b], "greater_than",
                            f"في القيم المعروضة لعام {year} للمؤشر «{a['indicator_ar']}»، هل قيمة {a['economy_ar']} أكبر من قيمة {b['economy_ar']}؟ قارن الأرقام المسجلة فقط وأعد قيمة منطقية.",
                            f"For the displayed {year} values of {code}, is {left} greater than {right}? Compare recorded numbers only and return a boolean.")
    questions.sort(key=lambda x: x["id"])
    table_rows = sorted(tables.values(), key=lambda x: x["table_id"])
    # Explicit typed Parquet schemas are inferred from nonempty complete configuration rows.
    import pyarrow as pa
    import pyarrow.parquet as pq
    for config, rows in [("observations", observations), ("questions", questions), ("tables", table_rows)]:
        for split in ("train", "validation", "test"):
            subset = [x for x in rows if x["split"] == split]
            write_jsonl(release / "jsonl" / config / (split + ".jsonl"), subset)
            target = release / "data" / config / (split + "-00000-of-00001.parquet")
            target.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(pa.Table.from_pylist(subset), target, compression="zstd")
    write_json(release / "series.json", list(series_info.values()))
    write_json(release / "splits.json", {"method": "SHA256 order of bayanat-public-data-v0.1:<ISO3>; first 16 train, next 3 validation, last 3 test", "economies": split_map, "second_highest_years": "test-only question-structure diagnostic, not included in the shared-operator score"})
    stats = {"version": "0.1.0", "source": "World Bank WDI, source 2", "source_snapshots": source_snapshots,
             "economies": len(ECONOMIES), "indicators": len(SERIES), "years": [2000, 2024],
             "observations": len(observations), "nonnull_observations": sum(x["value"] is not None for x in observations),
             "missing_observations": sum(x["value"] is None for x in observations), "question_records": len(questions),
             "unique_task_families": len(set(x["family_id"] for x in questions)), "unique_tables": len(tables),
             "operations": dict(collections.Counter(x["operation"] for x in questions)),
             "answer_statuses": dict(collections.Counter(json.loads(x["gold_answer"])["status"] for x in questions)),
             "per_split": {split: {"economies": sorted(c for c, s in split_map.items() if s == split),
                 "observations": sum(x["split"] == split for x in observations),
                 "questions": sum(x["split"] == split for x in questions),
                 "tables": sum(x["split"] == split for x in table_rows),
                 "structure_holdout_diagnostic": sum(x["split"] == split and x["structure_holdout_diagnostic"] for x in questions)} for split in ("train", "validation", "test")}}
    write_json(release / "stats.json", stats)
    examples = []
    for op in sorted(stats["operations"]):
        candidates = [q for q in questions if q["operation"] == op and q["split"] == "test"]
        if candidates:
            examples.append(candidates[0])
    missing_cases = [q for q in questions if json.loads(q["gold_answer"])["status"] == "missing"]
    if missing_cases:
        examples.append(missing_cases[0])
    write_jsonl(release / "examples.jsonl", examples)
    write_json(release / "build_manifest.json", {"raw_manifest_sha256": hashlib.sha256((raw / "manifest.json").read_bytes()).hexdigest(),
               "generation": "deterministic, no model calls or random paraphrase resampling", "decimal_arithmetic": "Python Decimal, derived outputs six decimal places ROUND_HALF_UP; lookup uses exact displayed source string", "version": "0.1.0"})
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
