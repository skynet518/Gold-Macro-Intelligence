# Output status contract

[中文](STATUS.zh-CN.md) · [Home](../README.md)

These fields describe different dimensions and are not interchangeable. Paths below are relative to each command's JSON root; fields are not guaranteed across commands. Preserve unknown values and inspect the relevant command's output rather than mapping these strings to a single success flag.

| Command | JSON path | Meaning |
|---|---|---|
| `analyze` | `model_status: UNCALIBRATED` | Model calibration status; no validated predictive model. |
| `analyze` | `market_research_judgment: RESEARCH_ONLY` | Research use boundary, not a validation result. |
| `analyze` | `model_signal_eligible: false` | No eligibility for a model trading signal. `market_signal.type` is `MANUAL_HYPOTHESIS`; it is not a model prediction. |
| `risk-check` | `model_status` and `market_signal.model_signal: NO_VALIDATED_SIGNAL` | No validated model signal; risk actions reflect user assumptions. `final_action` may be `RESEARCH_ONLY` or another risk action. |
| `walk-forward` | `status: NO_GO` | Insufficient rows for train, validation and test; see `reason`. |
| `walk-forward` | `status: RESEARCH_ONLY`, `model_signal: NO_VALIDATED_SIGNAL` | Mechanical research checks do not establish independent validation or trading eligibility; `reason` explains the boundary. |
| `harness-probe` | `real_model_status: NO_VALIDATED_SIGNAL`; `analysis.model_status`, `risk.model_status`, `walkforward.status` and `walkforward.model_signal` | Synthetic portability fixture carries these separate engine results, not real-market validation. |
| `harness-verify` | `comparison_status: MATCH` | Canonical JSON matches the expected fixture only; it does not validate a trading signal. |

`RESEARCH_ONLY` must never be interpreted as evidence of a validated or tradable signal. `NO_GO` and `NO_VALIDATED_SIGNAL` are not automatically promoted by a successful command or `MATCH`.
