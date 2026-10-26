---
pretty_name: Bayanat Arabic Public Data Reasoning
language:
- ar
- en
license: cc-by-4.0
task_categories:
- question-answering
size_categories:
- 1K<n<10K
annotations_creators:
- machine-generated
language_creators:
- found
- machine-generated
tags:
- arabic
- numerical-reasoning
- table-question-answering
- world-bank
- evidence-grounding
- tabular
- synthetic-questions
configs:
- config_name: questions
  default: true
  data_files:
  - split: train
    path: data/questions/train-*.parquet
  - split: validation
    path: data/questions/validation-*.parquet
  - split: test
    path: data/questions/test-*.parquet
- config_name: observations
  data_files:
  - split: train
    path: data/observations/train-*.parquet
  - split: validation
    path: data/observations/validation-*.parquet
  - split: test
    path: data/observations/test-*.parquet
- config_name: tables
  data_files:
  - split: train
    path: data/tables/train-*.parquet
  - split: validation
    path: data/tables/validation-*.parquet
  - split: test
    path: data/tables/test-*.parquet
---

# Bayanat Arabic Public Data Reasoning

**6,419 controlled Arabic questions over 4,400 real World Bank observations. Exact answer programs, visible source cells, and economy-disjoint splits.**

Use this dataset to test whether an Arabic system reads a recorded statistical value, compares the right years, distinguishes percentage points from percent change, joins GDP to population, or abstains when the visible data are missing or units cannot be added. Every question has a controlled English counterpart; the primary input is Arabic. This is an original task construction over a frozen source snapshot, rather than a translation of an existing QA benchmark.

[Company release page](https://www.bayanatlabs.com/open/arabic-public-data-reasoning) · [Dataset](https://huggingface.co/datasets/Bayanat-Labs/arabic-public-data-reasoning) · [Versioned source](https://github.com/Bayanat-Labs/arabic-public-data-reasoning/tree/v0.1.0) · [Local sample explorer](explorer.html)

The **facts and native Arabic indicator/economy names come from World Development Indicators**. Bayanat assembled the source snapshot, selected and represented the cells, authored controlled Arabic/English question templates with AI assistance, and generated answers with software. Questions, gold answers, citation targets and table views are **machine-generated annotations**, with no native-speaker or statistician validation established. No source observations were invented. The 6,419 tasks reuse 4,328 of the 4,400 source cells; questions and views are correlated observations and must not be counted as independent real-world facts.

## Load and use

```python
from datasets import load_dataset
import json

questions = load_dataset("Bayanat-Labs/arabic-public-data-reasoning", "questions", split="test")
row = questions[0]
model_visible = {"question_ar": row["question_ar"], "table": json.loads(row["context"])}
# Pass only model_visible and the public answer contract to a model.
# Never pass gold_answer, gold_evidence_ids, program, operation, template_id,
# family_id, diagnostic flags, source lookup tables or the complete dataset row.
```

`code/model_input.py` implements this whitelist and provides the answer contract. The `questions` configuration includes a JSON-string context, a formal program, a JSON-string gold answer and evidence IDs. The `observations` configuration retains all 4,400 selected real cells, including 100 missing values; `tables` contains 4,141 distinct generated visible contexts. JSONL equivalents are supplied in `jsonl/`. All train, validation and test gold is public.

Return an answer object with `status`, `value`, and `unit`, plus a separate `evidence_ids` list of visible cell IDs. A numeric `value` is a decimal string; comparison returns a JSON boolean; rank returns an ascending list of year strings. For a missing cell return `{"status":"missing","value":null,"unit":"<the cell unit_code>"}`. Incompatible addition returns `{"status":"incompatible_units","value":null,"unit":null}`. These schema snippets are illustrative, not answers to a released item.

## Measured contents

The frozen cohort contains 22 selected Arab League economies, eight explicitly licensed WDI indicators and 25 requested years, 2000–2024. The cohort is a current selection, not a reconstruction of historical membership or boundaries. Source names are preserved, including the World Bank's economy naming. **4,300 cells are numeric; 100 are missing.** An API `lastupdated` value of 2026-10-08 accompanies all eight collected observation responses, retrieved on 2026-10-26. Indicator metadata and provider statements remain separately inspectable in `series.json` and `raw/`.

| Split | Economies | Source observations | Questions | Test-only structure diagnostic |
|---|---:|---:|---:|---:|
| train | 16 | 3,200 | 4,654 | 0 |
| validation | 3 | 600 | 832 | 0 |
| test | 3 | 600 | 933 | 113 |

| Operator | Questions |
|---|---:|
| `difference` | 438 |
| `gdp_per_capita_join` | 542 |
| `greater_than` | 1,735 |
| `incompatible_sum` | 109 |
| `lookup` | 893 |
| `maximum_years` | 863 |
| `minimum_years` | 863 |
| `percentage_point_difference` | 425 |
| `relative_change` | 438 |
| `second_highest_years` | 113 |

Only 28 questions have the `missing` target and 109 have `incompatible_units`; the other 6,282 have `ok`. Report status metrics by class: an always-`ok` style method can achieve high status accuracy without computing correct values. Lookup questions are deliberately easy and form 893 records. The eight series cover population, current-dollar GDP, published current-dollar GDP per capita, annual GDP growth, life expectancy, electricity access, consumer-price inflation, and urban population share. See [SOURCES.md](SOURCES.md) for exact IDs, providers and licenses.

## Arithmetic and task boundaries

Lookup answers reproduce the exact displayed source numeric string. Arithmetic uses Python `Decimal`, with derived outputs rounded to six decimal places using `ROUND_HALF_UP`; trailing zeros can be omitted under numeric normalization. Values are never rounded before display and then secretly computed from hidden precision. Missing values stay `null`, rather than zero. Relative change requires a positive base and applies only to quantity series, not percentage rates. Rate differences use percentage points. Negative signed differences are retained.

The GDP/population task divides the two displayed source values for the same economy and year. It is explicitly a **calculated ratio**, which need not equal the separately published GDP-per-capita series. Current-dollar GDP changes are changes in recorded nominal values, not real economic growth. Comparisons of urban population shares concern recorded values; national definitions can differ. Ranking questions concern only non-missing cells actually displayed, return all ties, and do not establish a ranking over absent years or all economies. Cross-economy questions name both displayed economies and never claim to cover the full cohort.

`second_highest_years` is a test-only question-structure diagnostic over the second **distinct** highest value. Its 113 rows must be reported separately from the 6,306 rows using shared operators. Its parser is explicitly implemented in the symbolic baseline, so that baseline is not a demonstration of learning an unseen operation.

## Splits, duplication and evidence

Economies are assigned by a fixed SHA256 ordering, with 16 in train, three in validation and three in test; [splits.json](splits.json) contains the exact algorithm and allocation. All years, series, question families, joins and tables involving an economy stay in its split. Cross-economy comparisons are constructed only within a split. Source-cell and economy overlap across splits is zero under the audit. Indicator definitions, question grammar and numerical values can recur, so this is a narrow economy holdout with a separate operator diagnostic, not broad out-of-distribution evidence.

Exact context/question inputs and IDs are deduplicated. Related tasks can reuse a source cell inside a split. `family_id` identifies the operator and its ordered evidence cells; it does not make reused-source families statistically independent. For uncertainty estimates, cluster at least by economy or connected source-cell groups rather than individual question rows. Only three held-out economies are available in either validation or test, so inference beyond this cohort is limited.

Evidence IDs are the cells read by the formal answer program. They form an auditable software reference, not a human proof or a uniquely minimal explanation. **Contexts contain only the program's evidence cells**, so citing every displayed cell satisfies the evidence target. Citation scores here do not measure distractor rejection, retrieval quality, or faithful internal reasoning.

## Reproduce, verify and score

```sh
python -m pip install -r requirements.txt
python code/build.py --project . --output ../rebuilt-public-data
python code/verify.py --release . --raw raw --output reports/validation-rerun.json
python code/tests.py -v
python code/baselines.py --release .
python code/score.py --release . --split all \
  --predictions reports/template_aware_symbolic.predictions.jsonl \
  --output reports/symbolic-score-rerun.json
```

Rebuilding uses frozen `raw/` bytes and checks their hashes; it does not contact the API. `code/fetch.py` is the bounded acquisition recipe. Running it with `--refresh` explicitly starts a fresh mutable source collection. The original receipt URLs, retrieval times, successful HTTP status, hashes and source update fields are retained. The tested packaging environment used Python 3.14 and PyArrow 26.0.0. `code/verify.py` independently implements the algebra and source checks without importing the generator's oracle.

To score a model, write JSONL rows as `{"id":"<question id>","answer":{"status":"ok","value":"<answer>","unit":"<unit>"},"evidence_ids":["<visible cell id>"]}`. Use `--split test` for a test-only submission; default scoring includes both shared and diagnostic rows and reports each separately. A submission must use only the IDs in its selected scope. Missing predictions are wrong; duplicate, unknown or out-of-scope prediction IDs fail the submission. Nonfinite values fail numeric matching. Boolean values remain distinct from numeric 0/1; exact rank matching requires ordered string years. Nonexistent or duplicated citations fail strict joint. See [EVALUATION.md](EVALUATION.md).

## Actual validation and transparent baselines

The software auditor passed all 6,419 released tasks, all 4,400 source observations, raw snapshot hashes, source licenses, context/source equivalence, Parquet/JSONL parity, evidence sufficiency and split boundaries. Separate agent review independently recomputed every task at Decimal precision 60 and found no mismatches; this is software review, not native-speaker or domain-professional review. Exact reports are in `reports/`.

| Input-only method | Rows | Exact answer |
|---|---:|---:|
| Return first visible cell | 6,419 | 893/6,419 (13.91%) |
| Template-aware symbolic parser | 6,419 | 6,419/6,419 (100.00%) |

The symbolic parser recognizes every declared authored Arabic template, including the diagnostic operator, then applies an exact programmed calculation to visible cells. This demonstrates a controlled-format ceiling. It is not a learned-model result, unrestricted Arabic parser, or evidence of training benefit. The first-cell method has 98.30% status accuracy despite only 13.91% exact answers, illustrating why status alone is insufficient. No LLM benchmark score is claimed. Frozen prediction rows and per-split/per-operator results are included.

## Rights, credits and limitations

Data and original annotations/documentation are distributed under [CC BY 4.0](DATA_LICENSE.txt); **World Bank source data additionally retain the mandatory source terms** documented in [DATA_LICENSE.md](DATA_LICENSE.md), [ATTRIBUTION.md](ATTRIBUTION.md), and the frozen rights pages. Code is separately [Apache-2.0](code/LICENSE). Each of the eight individual series explicitly reports CC BY-4.0 in its frozen metadata. World Bank and the original data providers receive attribution; neither endorses this adaptation. No third-party benchmark examples, article prose, microdata or model responses are redistributed.

Limitations include controlled template language, limited operators, uneven source coverage and metadata quality, possible estimation/revision and cross-country definitional differences, rare missing-value targets, no distractor evidence, only three economies per held-out split, and public answers/programs that permit contamination. Software checks establish consistency with the frozen displayed source, not the truth of every economic claim or readiness for consequential decisions. This release makes no first/largest or guaranteed adoption claim.

Related resources include [Arabic WikiTableQA](https://www.mdpi.com/2079-9292/14/19/3829), [AraTable](https://github.com/rana-alshaikh/AraTable-Benchmark), [SAHM](https://mbzuai-nlp.github.io/SAHM/), and [ArabicNumBench](https://arxiv.org/abs/2602.18776). The contribution is this particular official-source snapshot, original controlled tasks, explicit rights provenance, exact executable answers and economy-held-out packaging.

```bibtex
@dataset{bayanat_arabic_public_data_reasoning_2026,
  author = {{Bayanat Labs}},
  title = {Bayanat Arabic Public Data Reasoning},
  year = {2026},
  version = {0.1.0},
  url = {https://huggingface.co/datasets/Bayanat-Labs/arabic-public-data-reasoning},
  note = {Controlled Arabic QA over real World Bank WDI observations; CC BY 4.0 with retained source terms}
}
```
