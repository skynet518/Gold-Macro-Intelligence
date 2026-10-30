# Research methodology

[简体中文](METHODOLOGY.zh-CN.md) · [Home](../README.md)

GMI is designed to make a gold-market argument inspectable. A calculation should identify which price series was used, when a data point was observed, when it was made public, and which transformation was applied. It does not assume that six market variables can be added into a single predictive number without a held-out test.

## 1. Drawdowns and recovery

For a consistent price series, the running high is the highest observed price up to a date. Drawdown is `price / running_high - 1`. Each retrospective episode follows the high through its trough and the first observation that regains the high. The engine also records the first time a chosen drawdown threshold was breached; that observable event must be kept separate from the eventual trough, which is known only in hindsight.

An episode that has not regained the prior high is **right-censored**. Kaplan–Meier-style recovery summaries are descriptive and depend on the selection and observation window. A small number of major bear markets is not sufficient for precise conditional probabilities. When the input contains monthly averages, the system reports month-based timing rather than pretending to know intra-month highs or trading-day duration.

The historical World Bank-based study has a documented definition break in 2025 between London PM fixing averages and the later spot average series. The segments are studied separately; their peaks should not be connected as if they were one unchanged instrument. Any user-supplied data should preserve price type, unit, currency, frequency and provider identity.

## 2. Rates and dollar

The macro overlay uses available FRED series: `DGS2`, `DGS10`, `DFII10`, `T10YIE` and `DTWEXBGS`. `DFII10` is a ten-year TIPS real yield, not a daily “Fed rate”; `DTWEXBGS` is a broad trade-weighted dollar index, **not** ICE DXY. Rate levels and rate *changes* answer different questions. Historical event overlays are descriptive if original publication or vintage evidence is absent.

Do not treat the approximate identity between nominal yields, real yields and breakeven inflation as three independent regressors without considering collinearity and market conventions.

## 3. Futures positioning

CFTC disaggregated futures-only reports split gold positions among producers/merchants, swap dealers, managed money, other reportables and nonreportables. A managed-money net position is `long - short`; normalized crowding uses net positions relative to open interest. A smaller net long can arise from long liquidation, new shorts or both. Swap-dealer net shorts may reflect customer hedges rather than a directional bank view.

A Tuesday position snapshot is not necessarily available on Tuesday. GMI tracks available publication evidence and refuses to convert a website update date into a claimed first-release timestamp. Reports downloaded from a later annual archive cannot establish the exact historical vintage on their own.

## 4. ETF and central-bank demand

Reported ETF gold holdings are a stock; a change in holdings is not automatically identical to a reported dollar fund flow. A central bank's reported gold stock, the monthly change in that stock and an independently verified market purchase are distinct measurements. GMI aligns country-level changes to comparable reporting months, checks missing months, and records coverage and data revisions. A larger holding valuation due to a higher gold price does not imply a purchase.

## 5. Liquidity, options and six-factor research

The remaining evidence streams are only comparable when their definitions, units and publication timing are clear. The six research categories are rates/dollar, futures positioning, ETF/physical, central banks, liquidity and options/market structure.

The factor module supports rolling historical ranks and exploratory forward-return associations. Data coverage can be incomplete; unavailable modules are shown as unavailable, not silently scored zero. User-supplied module weights are uncalibrated hypotheses. A descriptive rank or Pearson correlation does not establish a trading edge or causality.

## 6. Walk-forward testing and risk

The walk-forward component separates training, validation and test periods and requires consistent source identity and input timing. It is a testing framework, not proof of valid forecasts: true point-in-time data, realistic executable prices, signal provenance, transaction costs and funding assumptions must still be established. Monthly average prices are not a tradeable execution quote. Brokerage execution and sizing are not implemented.

Risk checks are separate from market views. Hitting a position cap blocks adding exposure; it is not a bearish macro signal. Any reduction due to a risk threshold must be labeled as a risk action, not evidence that a forecasting model is short gold.

**Current model eligibility: `NO_GO / NO_VALIDATED_SIGNAL`.** Until auditable data and out-of-sample evidence support a model, the output remains research-only.
