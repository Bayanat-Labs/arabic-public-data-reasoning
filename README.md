# Arabic Public Data Reasoning — source v0.1.0

Compile and score controlled Arabic numerical questions over a frozen snapshot of real World Bank World Development Indicators. The released dataset has **6,419 generated task families, 4,400 real observations, 4,141 visible tables, 22 economies and eight indicators**, with economy-disjoint splits. Questions and software gold use newly authored AI-assisted templates, with no human linguistic/statistical validation established.

[Dataset v0.1.0](https://huggingface.co/datasets/Bayanat-Labs/arabic-public-data-reasoning/tree/v0.1.0) · [Explorer](https://huggingface.co/spaces/Bayanat-Labs/arabic-public-data-reasoning) · [Company release page](https://www.bayanatlabs.com/open/arabic-public-data-reasoning) · [Full dataset card](DATASET_CARD.md)

This source checkout contains code, tests, rights/citation documents and measured statistics. Real source rows, generated JSONL/Parquet, predictions and frozen rights-page evidence are on Hugging Face and are intentionally absent here. The full dataset card describes that download, not files already in this checkout.

## Quickstart

Unit, arithmetic, model-input and scorer mutation tests use only the standard library:

```sh
python code/tests.py -v
```

The complete rebuild uses Python 3.14, PyArrow 26.0.0 and the pinned public v0.1.0 raw snapshot. Public downloads require no token/account:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python code/download_snapshot.py --output work/snapshot
python code/build.py --project work/snapshot --output work/rebuilt
python code/verify.py --release work/rebuilt --raw work/snapshot/raw --output work/validation.json
python code/baselines.py --release work/rebuilt
python code/score.py --release work/rebuilt --split all --predictions work/rebuilt/reports/template_aware_symbolic.predictions.jsonl --output work/symbolic-score.json
```

The downloader verifies every file and the expected raw-manifest SHA256. A second build of all 23 generated files matched the release byte for byte. `python code/fetch.py --project work/fresh-snapshot` is the optional bounded API acquisition recipe with finite retries and receipts. A mutable fresh collection cannot reproduce historical bytes; use the pinned snapshot for v0.1.0 comparisons.

## Model boundary and evaluation

Pass only `code/model_input.py:model_input(question)` and its public answer contract to a model. Keep gold, programs, operators, template/family IDs and diagnostic flags out of inputs. All split gold is public and may be contaminated. [EVALUATION.md](EVALUATION.md) defines the prediction schema, numerical normalization and evidence rules. The scorer rejects duplicate/unknown IDs, distinguishes booleans from numeric 0/1, rejects nonfinite values and counts missing predictions as wrong.

The 113 test-only second-highest-distinct-value questions are reported separately from shared operators. `verify.py` independently recomputes answers without importing the generator oracle and checks source values, licensing, hashes, evidence and split boundaries. CI runs offline semantic and scorer/input mutation tests, without API/model calls or dataset downloads.

The first-cell baseline reaches 13.91% exact answers. The template-aware symbolic parser reaches 100% because every authored template and operator is explicitly implemented. These are transparent input-only rules, not learned-model results or training-benefit evidence. Contexts contain only relevant evidence cells, so citing every displayed cell passes the citation target; this does not test retrieval or distractor rejection.

## Rights and limits

Original code: **Apache-2.0** ([LICENSE](LICENSE)). Original templates, annotations and documentation: **CC BY 4.0**. Real WDI data retain the World Bank's mandatory additional dispute-resolution and attribution terms. Each selected series explicitly reports CC BY-4.0 in its metadata. See [DATA_LICENSE.md](DATA_LICENSE.md), [ATTRIBUTION.md](ATTRIBUTION.md), [SOURCES.md](SOURCES.md), and frozen evidence in the pinned dataset. Neither World Bank nor source providers endorses this adaptation.

The 100 missing observations remain null. Derived arithmetic uses displayed Decimal values, six decimals and HALF_UP. Rate differences use percentage points; relative changes require positive quantity bases. GDP/population is a calculated ratio, not necessarily the separately published per-capita series. Current-dollar GDP changes are not real economic growth. National definitions and estimates can differ.

There are only three test economies, controlled templates, rare abstention targets and public programs/answers. This does not establish generalization, production readiness, scientific comparability or model difficulty. No first/largest or guaranteed adoption claim is made. Cite [CITATION.cff](CITATION.cff) and credit World Bank WDI and individual providers.
