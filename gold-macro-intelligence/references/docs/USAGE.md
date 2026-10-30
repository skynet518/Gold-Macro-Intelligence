# Using GMI

[简体中文](USAGE.zh-CN.md) · [Home](../README.md)

## 1. Run the offline example

From the repository root, with Python 3.10+:


### Install the Python engine and Skill

Python 3.10+ is required. From the repository root on macOS / Linux, use an isolated environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python -m gmi env-check
.venv/bin/python -m gmi analyze examples/analysis.json
```

On Windows use `.venv\Scripts\python.exe` instead of `.venv/bin/python`. The Skill and Python engine are separate components: installing the Skill alone does not install the Python package. The host determines its Skill location; the Agent must use the interpreter with GMI installed and have authorized file and terminal access. With the required Python version, `python3 -m gmi` can also run directly from the source root. A fully offline environment may lack pip build dependencies; `pip install .` may need to fetch `setuptools>=68`. GMI does not automatically download, install or configure Agent hosts. See the [status contract](STATUS.md).

```bash
python3 -m gmi env-check --skill gold-macro-intelligence/SKILL.md
python3 -m gmi analyze examples/analysis.json
python3 -m gmi drawdowns examples/prices.json --threshold 0.10
python3 -m gmi backtest examples/backtest.json
python3 -m gmi harness-probe --input fixtures/gmi_portability_input.json --output gmi-result.json
python3 -m gmi harness-verify --candidate gmi-result.json --expected fixtures/gmi_portability_expected.json
```

All included quick-start inputs are synthetic. If `harness-verify` reports `MATCH`, the calculation agrees with the fixed example; this does not establish predictive value. `--output` writes JSON to a file where supported.

## 2. Run from an Agent Skill

1. Make the `gold-macro-intelligence/` directory discoverable under a skill location supported by your host.
2. Make the `gmi` Python package importable in the execution environment (from the repository root or using `python3 -m pip install .`).
3. Ask your agent to analyze a **specific file** and to run the matching `python3 -m gmi ...` command. For example: “Use GMI to review `my-gold-research.json`, show the data dates and missing inputs, and do not infer trades.”
4. Verify the structured output. An agent's prose answer is not a substitute for running the engine.

The Skill uses the Agent Skills folder format, but hosts differ in their filesystem and process permissions. No host is assumed to support arbitrary Python execution by default.

## 3. Prepare input data

For basic analysis, use the field layout in `examples/analysis.json`: each observation has a module, metric, numeric value, unit, time fields (`observed_at`, `published_at`, `retrieved_at`), provider/source, URL and vintage. CFTC requires a matching category and report definition; central-bank input requires country identity. Follow the accepted metrics and units in the engine's validation dictionary. Unknown timing or incompatible units should be fixed at the source rather than guessed.

A simple CSV adapter is available:

```bash
python3 -m gmi import-csv my-observations.csv --output normalized.json
```

Do not treat the example's observation values or dates as market evidence.

## 4. Market-data research (requires external files)

CFTC Disaggregated Futures Only source files can be downloaded from the official archive. FRED can be imported or cached using its supported series; review its terms before downloading. A documented research command is:

```bash
python3 -m gmi update-report \
  --cftc /path/to/official-cftc-file.zip \
  --releases /path/to/verified-release-bounds.json \
  --fred-cache /path/to/fred-cache \
  --output my-market-report.json --markdown my-market-report.md
```

You must prepare the official files, release evidence and FRED cache yourself. `--fetch-fred` can request official FRED snapshots (subject to access and availability); those snapshots remain **descriptive**, not full point-in-time archives. A CFTC website's page-update time is not proof of original release time. ETF/central-bank supplements require properly sourced user input.

For historical event research, `event-study` requires **two separately identified** price inputs (`--fixing`, `--spot`) and one of `--fred-cache` or `--fred-anchors`; a later downloaded FRED snapshot or anchors from a previous report cannot certify historical trading-time availability. See [methodology](METHODOLOGY.md) and [data sources](DATA_SOURCES.md).

For `walk-forward`, the built-in verified identity mappings currently cover FRED `DFII10`, `DGS2`, `DGS10`, `T10YIE` and `DTWEXBGS` with their dictionary units and series URLs. Other known metrics without a registered mapping fail closed. Unknown raw metrics require an explicit custom feature contract; see `examples/v060_walkforward_synthetic.json`. These checks do not independently verify the provider or historical vintage.

## 5. Read the output correctly

- `NO_GO / NO_VALIDATED_SIGNAL` means a live predictive rule has not passed the required data and validation checks.
- A risk gate can block adding to a position without making a bearish market call.
- Missing factors are displayed as missing; a six-part score cannot be claimed when most modules have no valid data.
- Synthetic backtest returns must never be cited as actual gold strategy performance.

The engine does not send orders. See [limitations](LIMITATIONS.md) before making decisions involving capital.
