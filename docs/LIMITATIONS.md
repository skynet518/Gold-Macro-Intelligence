# Validation status and limitations

[简体中文](LIMITATIONS.zh-CN.md) · [Home](../README.md)

**Project status: research-only. Real strategy eligibility: `NO_GO / NO_VALIDATED_SIGNAL`.** A successfully installed Skill or a passing unit test is evidence that a software behavior works, not that a trade will make money.

## What is verified as software

GMI provides deterministic analysis, input checks, CFTC report parsing, drawdown/recovery calculations, a historical event overlay, factor research interfaces, a walk-forward testing framework, risk checks and synthetic fixture comparison. A public v1.0 release should claim only what its final clean-environment test logs actually prove.

## What is not established

- Historical point-in-time correctness for complete real-data strategies: published and retrieved times, archived vintages and revisions are not fully available across providers.
- Full six-factor real-data coverage: central bank, ETF, liquidity and option histories are not all supplied through ready-to-run free connectors.
- Tradable execution-price history for every period: monthly average gold prices are descriptive, not trade fills.
- Statistical significance, stability or economic profitability of a combined signal across unseen periods.
- Universal compatibility with every agent host or the right to run code in that host.

The six factors should not be scored as zero when unavailable. A provider's data revision can change retrospective results. CFTC positions do not identify every trader or prove why an individual traded. Country reserve-stock changes are not verified cash transactions. A risk-driven reduction is not the same as an evidence-based bearish forecast.

## Safe use

Use output to structure questions, audit historical episodes and identify what changed. If you want to make a position decision, supplement this research with independent source verification, instrument-specific market conditions, liquidity needs and your own risk constraints. GMI has no broker execution or automatic portfolio modification.

Report reproducibility depends on licensed input files, their actual release times, version identity and transformation code. If any of these are missing, the research should carry a visible limitation rather than a false confidence score.
