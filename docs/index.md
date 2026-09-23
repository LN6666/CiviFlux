# 文档导航

## 当前产品与接续

| 问题 | 入口 |
|---|---|
| 项目现在是什么、怎样开始 | [README](../README.md) |
| 其他 Codex 账户如何轮替接手 | [CODEX_HANDOFF](CODEX_HANDOFF.md) |
| 本次对话每项用户要求落实在哪里 | [USER_REQUIREMENTS_TRACE](USER_REQUIREMENTS_TRACE.md) |
| 用户决定及旧方案覆盖关系 | [USER_DECISIONS](../execution/USER_DECISIONS.md) |
| 怎样安装、运行、测试、看失败 | [CURRENT_RUNBOOK](CURRENT_RUNBOOK.md) |
| Helsinki 官方单位与入口的独立证据 | [SERVICE_MAP_ENTRANCE_EVIDENCE](SERVICE_MAP_ENTRANCE_EVIDENCE.md)；道路接入仍未核验 |
| 代码职责、数据流、扩展位置 | [CURRENT_ARCHITECTURE](CURRENT_ARCHITECTURE.md) |
| 新开发者如何接手 | [DEVELOPMENT](../DEVELOPMENT.md) |
| 工程约束与交付标准 | [CONTRIBUTING](../CONTRIBUTING.md) |
| Git、版本与交接规则 | [VERSIONING](VERSIONING.md) |
| 已接受的架构决策 | [ADR 0001](adr/0001-current-architecture.md) |
| PPR 算法选择与误差边界 | [ADR 0002](adr/0002-pagerank.md) |
| 范围、证据与工程风险约束 | [ARCHITECTURE_GUARDRAILS](ARCHITECTURE_GUARDRAILS.md) |
| 历史道路/火灾扰动怎样回测、目前缺什么证据 | [HISTORICAL_BACKTEST_PROTOCOL](HISTORICAL_BACKTEST_PROTOCOL.md) |
| SimpleJev 状态、可选 Qwen 比较与付费调用暂缓 | [模型 adapter](../adapters/system_one/README.md) |
| 当前 checkpoint/必须 gate | [execution/STATE](../execution/STATE.md) 与 `evidence/` |

## 历史来源工程包：不作为当前运行指令

`00_PRODUCT.md`–`15_COMPETITIVE_BENCHMARK.md`、`../prompts/` 和 `../MASTER_PLAN.md` 是原始设计/验收来源。`../tests/` 与 `../verification/` 是独立参考检查。保留它们是为追溯和独立验证，不代表当前产品尚未实现，也不意味着全部 gate 已完成。

当前用户指定 **Featherless SimpleJev 的 Qwen classifier**，选择远程 API 而非本地部署；生产付费调用为 `DEFERRED_USER`，公开 demo 验证单列。普通生成式 Qwen 只是可选比较，不能替代该 typed classifier。来源文件中的本地 GPU/权重部署要求不再适用，模型真实性、物理隔离、预算与 provenance 要求继续适用。

尤其是 [13_JEV_TO_QWEN_MIGRATION](13_JEV_TO_QWEN_MIGRATION.md)、[05_QWEN_SYSTEM_ONE](05_QWEN_SYSTEM_ONE.md) 及来源 prompts 中的 local Reflex/Qwen 部署方案，仅保留历史追溯。当前迁移覆盖关系以 [USER_DECISIONS](../execution/USER_DECISIONS.md)、[运行手册](CURRENT_RUNBOOK.md) 和 [SimpleJev adapter](../adapters/system_one/README.md) 为准；不能据旧文档重新启动本地模型工作或开通生产付费调用。来源里的未实施状态也不能覆盖当前 STATE 与可核查测试证据。

[HANDOFF_README](HANDOFF_README.md) 为原始 README 快照。接手时按当前文档和 STATE 找到 active work package，只读取该包必要的来源细节；不要反复把 MASTER_PLAN 当作运行状态，也不要修改原始 oracle 迎合产品输出。
