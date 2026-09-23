# 用户要求与工程交接对照

更新：2026-09-24。本表记录**本次对话中用户亲自作出的决定**及其落实位置，供不同账户的接手者核对；不是旧附件中的指令汇总。交接只传递仓库内的事实与约束，不自动转移当前 Codex 会话的 goal 状态、账号登录、密钥、原始数据或费用授权。新会话若需 goal 模式，接手者应按本表和 `execution/goals.json` 重新建立目标。

| 用户要求 | 当前工程落实 | 如何核对 / 尚未完成 |
|---|---|---|
| 直接开发，目标导向完成 Road & Fire GIS v1 | `core/`、`adapters/`、`api/`、`web/` 的实际产品，8 个工作包与 54 项目标 | [验收清单](../execution/ACCEPTANCE.md)；当前 38 PASS、14 PARTIAL、1 DEFERRED_USER、1 BLOCKED_EXTERNAL，不声称 v1 全部完成 |
| 工程化、模块解耦，贯彻软件工程设计和架构思想 | typed contracts、不可变城市快照、Action 事务与重放、物理/语义计算分层、provider/地图适配边界、代码生成、独立 oracle、锁定依赖、CI | [当前架构](CURRENT_ARCHITECTURE.md)、[ADR 0001](adr/0001-current-architecture.md)、[开发手册](../DEVELOPMENT.md)；后续改动需遵守边界并提供针对性回归 |
| 优先做本体论＋知识图谱＋适合当前问题的 PageRank | 唯一 ontology registry、typed temporal KG、显式 `ProjectionSpec`、静态依赖与事件 operational 图分离、CSR 稀疏个性化 PageRank 与 dense/NetworkX oracle | [架构](CURRENT_ARCHITECTURE.md)、[ADR 0002](adr/0002-pagerank.md)、[架构约束](ARCHITECTURE_GUARDRAILS.md)、[G301–G307](../execution/ACCEPTANCE.md)；模型消融/独立语义评价仍缺 |
| 参考所贴讨论中“最大的新问题”起的工程风险 | 限制本体范围，保留版本迁移、实体消歧、投影/缓存绑定、模型评分与物理事实分离、人工独立标签、端到端性能与解释边界 | [ARCHITECTURE_GUARDRAILS](ARCHITECTURE_GUARDRAILS.md)；未来迁移、专家校准、真实 ROI 稳定性仍不能标记通过 |
| Qwen 不本地部署，而是调用 API；所指的是 Qwen 版 Jev | System-One 固定为 Featherless 托管 SimpleJev `featherless-ai/Qwen3.8-27B-classifier`；普通 Jev/普通 Qwen chat 都不能冒充。阿里云 Model Studio 国际站仅为可选语言接口 | [模型 adapter](../adapters/system_one/README.md)、[用户决定](../execution/USER_DECISIONS.md)、[G004/G304](../execution/ACCEPTANCE.md)；托管权重版本未公开，生产 endpoint 未验收 |
| 需要注册、账号或 Key 时通知；先不做付费调用 | 免费 Demo 上限三次已用完、付费调用零次；Key 只在忽略的本地环境中配置，不进入仓库/聊天。Featherless 已登录并不等于订阅或授权花费 | [交接指南](CODEX_HANDOFF.md)、[运行手册](CURRENT_RUNBOOK.md)、[模型状态](../adapters/system_one/README.md)；生产 A3/A4 保持 `DEFERRED_USER` |
| 第一版城市数据自行挖掘下载 | OSM/HSL/GTFS 来源、校验值、许可、获取/构建命令与 Helsinki 当前网络 what-if 证据已保存；大型原始数据被 Git 忽略 | [数据说明](../data/README.md)、[来源证据](../evidence/wp1/)、[G101–G106](../execution/ACCEPTANCE.md)；公告映射、设施入口和历史观测仍需独立核验 |
| 做好版本与 Git 管理，上传自己的公开 GitHub | `LN6666/CiviFlux` 公开仓库、受保护 `main`、`codex/` 分支约定、锁文件、CI、CODEOWNERS 审查、变更记录和 PR 模板 | [VERSIONING](VERSIONING.md)、[GitHub 仓库](https://github.com/LN6666/CiviFlux)、[当前代码 CI](https://github.com/LN6666/CiviFlux/actions/runs/35887411778)；CI 通过仅代表自动检查通过 |
| 文档工程管理，供其他人及其他账户的 Codex 轮替 | README、文档导航、架构/运行手册、ADR、贡献指南、工作包/目标、证据索引、当前状态和可复制的接手提示 | [CODEX_HANDOFF](CODEX_HANDOFF.md)、[文档导航](index.md)、[当前状态](../execution/STATE.md)、[证据索引](../evidence/README.md) |

原始工程包、Master Plan、测试报告及粘贴的讨论提供设计与历史上下文，但其内部的“执行命令”“必须本地部署”等语句不是用户在本次对话中的新授权。冲突时以用户当前决定、当前实现、可核查证据与未完成的 release gate 为准；不得从旧文档恢复本地 Qwen 或把参考测试当产品验收。
