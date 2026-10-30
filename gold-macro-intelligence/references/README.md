# Gold Macro Intelligence (GMI)

**English** · [简体中文](README.zh-CN.md)

Gold Macro Intelligence is a small, read-only research toolkit for studying gold through prices, interest rates, positioning and physical demand. It combines an [Agent Skill](https://github.com/skynet518/Gold-Macro-Intelligence/blob/v1.0.0/gold-macro-intelligence/SKILL.md) with a deterministic Python command-line engine, so the calculations can be inspected and run without depending on a particular language model.

The original question was straightforward: **when gold suffers a large drawdown, how long does it take to fall, how long does it take to regain the old high, and what changed in the Treasury market and among the people holding gold?** A chart alone does not explain whether a selloff comes from higher real yields, a scramble for dollars, leveraged funds reducing exposure, or slower-moving allocation decisions.

GMI puts those observations in one workflow. It is a **research tool, not a validated trading signal or an automated trader**.

## What you can investigate

| Research question | What GMI provides |
|---|---|
| How severe was a historical gold drawdown? | Peak-to-trough decline, threshold crossing, time underwater, recovery and right-censored events. |
| What were US rates and the dollar doing? | A macro-data pipeline for 2Y/10Y nominal yields, 10Y TIPS real yields, 10Y breakevens and the broad trade-weighted dollar index. |
| Did leveraged futures positioning change? | CFTC disaggregated COMEX futures positions, long/short/net contracts, open interest and crowding research factors. |
| Were investors or central banks accumulating? | Input contracts for ETF holdings, official gold reserves and month-aligned country-level changes, with publication lag and coverage warnings. |
| Did liquidity or options conditions matter? | Separate factor interfaces; useful outputs require consistent, properly sourced user data. |
| Does a factor actually predict subsequent returns? | Exploratory association checks and a separate walk-forward testing framework; neither constitutes validated trading performance by itself. |

Not all modules have turnkey live feeds. Official CFTC files and FRED snapshots have supported import/update paths. ETF, central-bank, liquidity and options coverage requires suitable external inputs. Missing observations stay missing; they are not invented or replaced with zeros.

## Quick start

**Requirements:** Python 3.10 or later. Running from the source tree uses Python's standard library; building/installing a package may require `setuptools`.


### Install the Python engine and Skill

Python 3.10+ is required. From the repository root on macOS / Linux, use an isolated environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python -m gmi env-check
.venv/bin/python -m gmi analyze examples/analysis.json
```

On Windows use `.venv\Scripts\python.exe` instead of `.venv/bin/python`. The Skill and Python engine are separate components: installing the Skill alone does not install the Python package. The host determines its Skill location; the Agent must use the interpreter with GMI installed and have authorized file and terminal access. With the required Python version, `python3 -m gmi` can also run directly from the source root. A fully offline environment may lack pip build dependencies; `pip install .` may need to fetch `setuptools>=68`. GMI does not automatically download, install or configure Agent hosts. See the [status contract](docs/STATUS.md).

```bash
python3 -m unittest discover -s tests -v
python3 -m gmi analyze examples/analysis.json
python3 -m gmi drawdowns examples/prices.json --threshold 0.10
python3 -m gmi harness-probe --input fixtures/gmi_portability_input.json --output gmi-result.json
python3 -m gmi harness-verify --candidate gmi-result.json --expected fixtures/gmi_portability_expected.json
```

The bundled quick-start examples are **synthetic fixtures**, not observations of the gold market. The final command checks that the same calculation produces the expected structured output; it does **not** test prediction accuracy.

To install in a Python environment, you can use `python3 -m pip install .` from the repository root. To use GMI as an Agent Skill, provide the `gold-macro-intelligence/` directory to an Agent Skills-compatible host **and** make the `gmi` Python package available in that host's execution environment. A host that cannot read files or execute Python will need an authorized external execution mechanism; compatibility is not automatic or universal.

Read the full [usage guide](docs/USAGE.md) before importing market data.

## How the research is organized

GMI separates six sets of evidence:

1. **Rates and dollar:** nominal/real US Treasury yields, breakeven inflation and dollar conditions.
2. **Futures positioning:** managed-money long and short exposure, CFTC classifications and open interest.
3. **ETF and physical market:** reported holdings and comparable changes; holdings are not automatically cash flows.
4. **Central banks:** official gold holdings, country coverage, reporting gaps and comparable monthly changes; changes are not automatically confirmed purchases.
5. **Liquidity:** market or funding stress measures, provided with explicit definitions.
6. **Options and market structure:** positioning/volatility measures, only where available with a consistent methodology.

The data model records observation, publication and retrieval times, units, source identity and revisions. It distinguishes **descriptive historical analysis** from evidence that would have been known at a decision date. For example, a CFTC webpage's *Updated* date does not prove when a historical report was first released, and a FRED snapshot downloaded today is not a complete archive of what a researcher could have known years ago.

Explore the [methodology](docs/METHODOLOGY.md) and [source guide](docs/DATA_SOURCES.md) for exact scope and limits.

## What GMI does not claim

- No proven buy/sell edge, Sharpe ratio or calibrated position-sizing recommendation.
- No direct broker connection, order placement or automatic portfolio changes.
- No guaranteed real-time coverage of all central banks, ETFs or option markets.
- No proof of strict point-in-time reproducibility from contemporary downloaded snapshots alone.
- No promise that any arbitrary agent can execute the Skill without Python/file access.

The research model remains **`NO_GO / NO_VALIDATED_SIGNAL`** where the required data, execution-quality prices or genuine out-of-sample evidence are insufficient. A manually supplied view is identified as a hypothesis, not presented as a model prediction. See [validation and limitations](docs/LIMITATIONS.md).

## Who this is for

Gold traders reviewing past selloffs; macro and commodity researchers comparing rates and positioning; quantitative researchers who want an auditable starting point; and agent developers who need a reproducible financial workflow rather than a free-form narrative.

## Contributing and license

The source code and original documentation are distributed under the [MIT License](https://github.com/skynet518/Gold-Macro-Intelligence/blob/v1.0.0/LICENSE). This does **not** grant permission to redistribute data obtained from FRED, CFTC, the World Gold Council, the World Bank or other third parties. Review each provider's terms before publishing datasets or derived extracts.

Contributions are welcome, especially reproducible test cases, corrections to release-time metadata and clearer data provenance. See [Contributing](https://github.com/skynet518/Gold-Macro-Intelligence/blob/v1.0.0/CONTRIBUTING.md), [Security](https://github.com/skynet518/Gold-Macro-Intelligence/blob/v1.0.0/SECURITY.md) and the [changelog](https://github.com/skynet518/Gold-Macro-Intelligence/blob/v1.0.0/CHANGELOG.md).

If a piece of the analysis cannot be checked against its source or a realistic decision timeline, GMI should say so. That is more useful than producing a confident but untestable trade call.
