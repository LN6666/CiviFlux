# 用户要求与工程交接对照

更新：2026-09-26。本表记录**本次对话中用户亲自作出的决定**及其落实位置，供不同账户的接手者核对；不是旧附件中的指令汇总。交接只传递仓库内的事实与约束，不自动转移当前 Codex 会话的 goal 状态、账号登录、密钥、原始数据或费用授权。新会话若需 goal 模式，接手者应按本表和 `execution/goals.json` 重新建立目标。

| 用户要求 | 当前工程落实 | 如何核对 / 尚未完成 |
|---|---|---|
| 直接开发，目标导向完成 Road & Fire GIS v1 | `core/`、`adapters/`、`api/`、`web/` 的实际产品，8 个工作包与 54 项目标 | [验收清单](../execution/ACCEPTANCE.md)；当前 44 PASS、8 PARTIAL、1 DEFERRED_USER、1 BLOCKED_EXTERNAL，不声称 v1 全部完成 |
| 工程化、模块解耦，贯彻软件工程设计和架构思想 | typed contracts、不可变城市快照、Action 事务与重放、物理/语义计算分层、provider/地图适配边界、代码生成、独立 oracle、锁定依赖、CI | [当前架构](CURRENT_ARCHITECTURE.md)、[ADR 0001](adr/0001-current-architecture.md)、[开发手册](../DEVELOPMENT.md)；后续改动需遵守边界并提供针对性回归 |
| 优先做本体论＋知识图谱＋适合当前问题的 PageRank | 唯一 ontology registry、typed temporal KG、显式 `ProjectionSpec`、静态依赖与事件 operational 图分离、CSR 稀疏个性化 PageRank、dense/NetworkX oracle 及冻结模型关系分数的离线置换对照 | [架构](CURRENT_ARCHITECTURE.md)、[ADR 0002](adr/0002-pagerank.md)、[架构约束](ARCHITECTURE_GUARDRAILS.md)、[G301–G307](../execution/ACCEPTANCE.md)；完整生产 A3/A4 消融和独立语义评价仍缺 |
| 参考所贴讨论中“最大的新问题”起的工程风险 | 限制本体范围，保留版本迁移、实体消歧、投影/缓存绑定、模型评分与物理事实分离、人工独立标签、端到端性能与解释边界 | [ARCHITECTURE_GUARDRAILS](ARCHITECTURE_GUARDRAILS.md)；未来迁移、专家校准、真实 ROI 稳定性仍不能标记通过 |
| Qwen 不本地部署，而是调用 API；所指的是 Qwen 版 Jev | System-One 固定为 Featherless 托管 SimpleJev `featherless-ai/Qwen3.8-27B-classifier`；普通 Jev/普通 Qwen chat 都不能冒充。阿里云 Model Studio 国际站仅为可选语言接口 | [模型 adapter](../adapters/system_one/README.md)、[用户决定](../execution/USER_DECISIONS.md)、[G004/G304](../execution/ACCEPTANCE.md)；托管权重版本未公开，生产 endpoint 未验收 |
| 需要注册、账号或 Key 时通知；先不做付费调用 | 免费 Demo 上限三次已用完、付费调用零次；Key 只在忽略的本地环境中配置，不进入仓库/聊天。Featherless 已登录并不等于订阅或授权花费 | [交接指南](CODEX_HANDOFF.md)、[运行手册](CURRENT_RUNBOOK.md)、[模型状态](../adapters/system_one/README.md)；生产 A3/A4 保持 `DEFERRED_USER` |
| 第一版城市数据自行挖掘下载 | OSM/HSL/GTFS 来源、校验值、许可、获取/构建命令与 Helsinki 当前网络 what-if 证据已保存；大型原始数据被 Git 忽略 | [数据说明](../data/README.md)、[边界敏感性负结果](../evidence/wp2/helsinki_boundary_sensitivity.json)、[G101–G106/G205](../execution/ACCEPTANCE.md)；正式边界、公告映射、设施入口和历史观测仍需独立核验 |
| 做好版本与 Git 管理，上传自己的公开 GitHub | `LN6666/CiviFlux` 公开仓库、受保护 `main`、`codex/` 分支约定、锁文件、CI、CODEOWNERS 审查、变更记录和 PR 模板 | [VERSIONING](VERSIONING.md)、[GitHub 仓库](https://github.com/LN6666/CiviFlux)、[最近 main CI](https://github.com/LN6666/CiviFlux/actions/runs/35887764508)；CI 通过仅代表自动检查通过 |
| 文档工程管理，供其他人及其他账户的 Codex 轮替 | README、文档导航、架构/运行手册、ADR、贡献指南、工作包/目标、证据索引、当前状态和可复制的接手提示 | [CODEX_HANDOFF](CODEX_HANDOFF.md)、[文档导航](index.md)、[当前状态](../execution/STATE.md)、[证据索引](../evidence/README.md) |
| 考虑浏览器性能 | 大 CityPack 道路选择按名称/ID 搜索且最多渲染 50 个选项；注意力每页 100 行并复用查询结果；真实后端浏览器 CI 验证。保留完整 API/ZIP 结果 | [Web 嵌入与性能边界](../web/README.md)、[GitHub CI](https://github.com/LN6666/CiviFlux/actions/runs/35922643950)；全量传输/跨设备内存和帧率仍待实测 |
| 扩展欧盟与伊斯坦布尔大型活动/F1 验证池并提醒 | 官方日期与封路来源候选、赛前冻结和赛后独立观测协议已记录；每周一的 Codex 事件 heartbeat 已启用 | [事件清单](EVENT_VALIDATION_WATCHLIST.md)、[回测协议](HISTORICAL_BACKTEST_PROTOCOL.md)；实际封路与路段级观测、权限/许可须按事件核验，不把日期当数值验证 |
| 优先按大型活动时间建设城市本体/KG；继续验证 Berlin，核查近日 Baku F1 | Berlin 与 Baku 固定来源、机动车 CityPack、typed KG 和 SHA 已生成；Berlin 与 Baku 均有独立多方式线性 KG，保留原机动车比较；Berlin 在新增公告封路开始前冻结了 3 组离线路径对照；Baku 官方 2026 公告及 AYNA 改线事实单独留卡 | [Berlin 城市图审计](../evidence/events/berlin-2026-city-kg-audit.json)、[Berlin 事前条件探针](../evidence/events/berlin-2026-incremental-pre-onset-probe.json)、[Baku 机动车图审计](../evidence/events/baku-2026-city-kg-audit.json)、[Baku 多方式图审计](../evidence/events/baku-2026-multimodal-kg-audit.json)、[Berlin 多方式图审计](../evidence/events/berlin-2026-multimodal-kg-audit.json)、[Baku 来源和可行性](BAKU_2026_F1_DATA_FEASIBILITY.md)；候选封路需人工有向映射核验，实际执行及独立交通观测未获得，V2/V3 不通过 |
| 扰动评估应考虑非机动车道路与步行区域 | Baku 从同一 OSM 源建立独立步骑线性候选 CityPack/KG，并在 GIS 图展示专用通道及明确 `area=yes` 的步行区域；另以可重放的假设 Action 探查 0.2 m / 15 m 走廊暴露和固定合成 OD 可达性；原 71.9% 公交公告街名重合比例保持只在机动车包上计算 | [Baku GIS 地图与计数](BAKU_2026_INDIRECT_GIS_COMPARISON.md)、[多方式 KG 审计](../evidence/events/baku-2026-multimodal-kg-audit.json)、[步骑间接探针](../evidence/events/baku-2026-active-indirect-probe.json)；步骑真实限制映射、路边人行道/过街连接审阅和实测影响均未完成，不输出真实步骑扰动分数；条件时间使用显式固定速度假设 |
| 如需订阅才通知 | 当前城市图、公告核查与离线探针均无模型费用，**目前无需订阅**；生产 classifier 与 A3/A4 完整实验仍被用户暂缓 | [用户决定](../execution/USER_DECISIONS.md)、[模型状态](../adapters/system_one/README.md)；若产生真实付费必要性，先说明用途、上限和估算，不自动启用 |

原始工程包、Master Plan、测试报告及粘贴的讨论提供设计与历史上下文，但其内部的“执行命令”“必须本地部署”等语句不是用户在本次对话中的新授权。冲突时以用户当前决定、当前实现、可核查证据与未完成的 release gate 为准；不得从旧文档恢复本地 Qwen 或把参考测试当产品验收。
