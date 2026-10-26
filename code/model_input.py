"""Pass only this whitelist to a model; never pass a complete questions row."""
import json


def model_input(question):
    return {"question_ar": question["question_ar"], "table": json.loads(question["context"])}


ANSWER_CONTRACT = {
    "status": "ok | missing | incompatible_units",
    "value": "numeric decimal string, boolean, ascending list of year strings, or null",
    "unit": "unit_code from table, percentage_points, percent_change, year, boolean, current_USD_per_person_calculated, or null for incompatible units",
    "derived_rounding": "six decimal places, ROUND_HALF_UP; trailing zeroes optional under numeric normalization",
    "lookup": "return the exact displayed numeric string; an empty value gives missing, null and its unit_code",
    "incompatible_units": "return null value and null unit",
}
