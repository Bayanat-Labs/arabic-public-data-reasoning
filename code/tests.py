#!/usr/bin/env python3
"""Semantic edge and mutation checks; no network or model calls."""
import copy
from decimal import Decimal
import json
import pathlib
import unittest
from verify import evaluate, normalized_decimal
from baselines import symbolic
from model_input import model_input
from score import value_equal, score_records, reject_constant


def cell(value, year="2000", **updates):
    row = dict(cell_id="c" + year, value=value, year=year, unit_code="persons", measure_kind="quantity",
               economy_code="X", indicator_code="SP.POP.TOTL")
    row.update(updates)
    return row


class ContractTests(unittest.TestCase):
    def test_decimal_half_up_and_zero(self):
        self.assertEqual(normalized_decimal("1.2345675", True), "1.234568")
        self.assertEqual(normalized_decimal("-1.2345675", True), "-1.234568")
        self.assertEqual(normalized_decimal("-0.0000001", True), "0")
        self.assertEqual(normalized_decimal("12000000"), "12000000")

    def test_missing_is_not_zero(self):
        self.assertEqual(evaluate("lookup", [cell(None)])["status"], "missing")
        self.assertEqual(evaluate("lookup", [cell("0")])["status"], "ok")
        with self.assertRaises(AssertionError):
            evaluate("difference", [cell(None), cell("1", "2001")])

    def test_signed_and_relative_change(self):
        rows = [cell("100"), cell("75", "2001")]
        self.assertEqual(evaluate("difference", rows)["value"], "-25")
        self.assertEqual(evaluate("relative_change", rows)["value"], "-25")
        with self.assertRaises(AssertionError):
            evaluate("relative_change", [cell("0"), cell("2", "2001")])
        with self.assertRaises(AssertionError):
            evaluate("relative_change", [cell("-1"), cell("2", "2001")])

    def test_percentage_points_not_percent(self):
        rows = [cell("5", measure_kind="rate"), cell("7", "2001", measure_kind="rate")]
        self.assertEqual(evaluate("percentage_point_difference", rows), {"status": "ok", "value": "2", "unit": "percentage_points"})
        with self.assertRaises(AssertionError):
            evaluate("relative_change", rows)

    def test_tied_and_second_distinct_rank(self):
        rows = [cell("10"), cell("10", "2001"), cell("8", "2002"), cell("8", "2003"), cell("2", "2004")]
        self.assertEqual(evaluate("maximum_years", rows)["value"], ["2000", "2001"])
        self.assertEqual(evaluate("second_highest_years", rows)["value"], ["2002", "2003"])

    def test_semantic_join_and_units(self):
        rows = [cell("10", indicator_code="NY.GDP.MKTP.CD", unit_code="current_USD"), cell("3", indicator_code="SP.POP.TOTL", cell_id="pop")]
        self.assertEqual(evaluate("gdp_per_capita_join", rows)["value"], "3.333333")
        bad = copy.deepcopy(rows)
        bad[1]["year"] = "2001"
        with self.assertRaises(AssertionError):
            evaluate("gdp_per_capita_join", bad)
        self.assertEqual(evaluate("incompatible_sum", rows)["status"], "incompatible_units")

    def test_symbolic_never_reads_gold(self):
        q = {"question_ar": "بحسب الخلية المعروضة، ما القيمة المسجلة؟", "context": json.dumps({"cells": [cell("3")]}),
             "gold_answer": '{"value":"999"}', "operation": "malicious_gold", "program": "hidden"}
        item = model_input(q)
        self.assertEqual(set(item), {"question_ar", "table"})
        self.assertEqual(symbolic(item)["value"], "3")
        item["table"]["cells"][0]["value"] = "4"
        self.assertEqual(symbolic(item)["value"], "4")
        with self.assertRaises(ValueError):
            symbolic({"question_ar": "سؤال غير مدعوم", "table": {"cells": [cell("3")]}})

    def test_scorer_boolean_is_not_number(self):
        self.assertFalse(value_equal(1, True))
        self.assertFalse(value_equal(False, "0"))
        self.assertTrue(value_equal(True, True))
        self.assertTrue(value_equal("3.000", "3"))
        self.assertFalse(value_equal("NaN", "3"))
        self.assertFalse(value_equal("Infinity", "3"))
        with self.assertRaises(ValueError):
            reject_constant("NaN")

    def test_scorer_rejects_duplicate_unknown_ids(self):
        q = dict(id="q", gold_answer='{"status":"ok","value":"3","unit":"persons"}',
                 gold_evidence_ids=["c"], split="test", operation="lookup", structure_holdout_diagnostic=False)
        p = dict(id="q", answer={"status": "ok", "value": "3.0", "unit": "persons"}, evidence_ids=["c"])
        self.assertEqual(score_records([q], [p])["groups"]["all"]["strict_joint_rate"], 1)
        with self.assertRaises(AssertionError):
            score_records([q], [p, p])
        with self.assertRaises(AssertionError):
            score_records([q], [dict(p, id="unknown")])
        self.assertEqual(score_records([q], [])["groups"]["all"]["answer_exact_rate"], 0)
        self.assertEqual(score_records([q], [dict(p, evidence_ids=["c", "unknown"])])["groups"]["all"]["strict_joint_rate"], 0)
        self.assertEqual(score_records([q], [dict(p, evidence_ids=["c", "c"])])["groups"]["all"]["strict_joint_rate"], 0)


if __name__ == "__main__":
    unittest.main()
