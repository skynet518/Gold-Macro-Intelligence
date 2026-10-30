# 输出状态契约

[English](STATUS.md) · [返回首页](../README.zh-CN.md)

这些字段描述不同维度，不能互相替代。以下路径均相对于各命令的 JSON 根节点；不同命令不保证包含相同字段。应保留未知值并检查对应命令的输出，不能统一映射为成功标志。

| 命令 | JSON 路径 | 含义 |
|---|---|---|
| `analyze` | `model_status: UNCALIBRATED` | 模型校准状态；没有经过验证的预测模型。 |
| `analyze` | `market_research_judgment: RESEARCH_ONLY` | 仅供研究的使用边界，并非验证结果。 |
| `analyze` | `model_signal_eligible: false` | 不具备模型交易信号资格。`market_signal.type` 为 `MANUAL_HYPOTHESIS`，是人工假设而非模型预测。 |
| `risk-check` | `model_status` 和 `market_signal.model_signal: NO_VALIDATED_SIGNAL` | 不存在已验证模型信号；风险动作基于用户假设。`final_action` 可能是 `RESEARCH_ONLY` 或其他风险动作。 |
| `walk-forward` | `status: NO_GO` | 训练、验证和测试所需行数不足；查看 `reason`。 |
| `walk-forward` | `status: RESEARCH_ONLY`、`model_signal: NO_VALIDATED_SIGNAL` | 机械研究检查不能证明独立验证或交易资格；`reason` 说明限制。 |
| `harness-probe` | `real_model_status: NO_VALIDATED_SIGNAL`；`analysis.model_status`、`risk.model_status`、`walkforward.status` 和 `walkforward.model_signal` | 合成可移植性样例携带各引擎结果，不是真实市场验证。 |
| `harness-verify` | `comparison_status: MATCH` | 仅表示规范化 JSON 与预期样例一致，不验证交易信号。 |

`RESEARCH_ONLY` 绝不能解读为交易信号已经验证或可以交易。命令成功或 `MATCH` 不会自动升级 `NO_GO`、`NO_VALIDATED_SIGNAL`。
