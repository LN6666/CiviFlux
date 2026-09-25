# Active user decisions

2026-09-23, current task:
- Directly implement the current CiviFlux engineering plan; goal mode enabled.
- **Qwen must be accessed through an API. Do not deploy Qwen locally or download model weights.**
- Notify the user whenever registration, account access, API credentials, or paid test authorization is needed.

These instructions supersede the imported handoff's mandatory local Reflex/Qwen deployment. API access must preserve the physical/semantic boundary, abstract-only prompts, typed validated responses, honest provider provenance, and real API-to-graph integration evidence. A structured completion score is not a Reflex token probability or a calibrated decision distribution. Provider/model selection is pending user input; missing credentials block only the corresponding live gate.

- Qwen provider: Alibaba Cloud Model Studio International (Singapore).
- Engineer for modularity, explicit interfaces and maintainability.
- Maintain Git version history and upload to the user’s own **public** GitHub repository `CiviFlux`; user authorization supersedes imported no-push default. Authentication pending.

- User explicitly defers paid Qwen calls. Keep QWEN_API_MAX_CALLS=0 and network egress disabled. Live API verification is DEFERRED_USER; continue every independent development task. Do not ask for an API key again until the user chooses to enable paid integration.

- Prioritize operational ontology, knowledge graph engineering and a currently maintained, suitable PageRank/PPR implementation; complete this core before optional comparison/polish. Jev account links requested for information only; no Jev paid calls authorized.

## Definitive provider correction — 2026-09-24

The user's screenshots identify **Featherless SimpleJev with Qwen3.8-27B-classifier** as the intended Qwen Jev-like System-One. This supersedes the earlier mistaken TypeSafe, ordinary DashScope, and remote Reflex interpretations for the classifier role. Use hosted API only; no model downloads or local deployment.

- Required classifier model: `featherless-ai/Qwen3.8-27B-classifier`.
- Free public demo: `https://simple-jev-demo-api.featherless.ai/v1/classifier`; no account or key. A bounded smoke may submit only abstract relation definitions and an objective, with at most 3 free calls, no automatic retry.
- Paid production: `https://api.featherless.ai/v1/classifier`; `FEATHERLESS_API_KEY`; calls remain disabled and DEFERRED_USER. The API key must stay in ignored local environment configuration.
- Optional language-interface LLM may use Alibaba Cloud Model Studio International, as previously selected; ordinary chat completion is not the SimpleJev classifier gate.
- Registration: https://featherless.ai/register ; key: https://featherless.ai/account/api-keys ; pricing: https://featherless.ai/docs/request-pricing-and-credits .
- Official contract verified at https://simple-jev.featherless.ai/docs . Expected-index score is normalized by `(rubric_levels - 1)` for semantic policy; it is not a calibrated probability.
- Latest architecture screenshot reconfirms ontology → runtime KG → GIS/SUMO projections → typed System-One semantic relation policy → personalized PageRank → optional language interface → embedded Web GIS. Physical metrics remain independent of semantic policy.

## 交接与账号边界 — 2026-09-24

- 用户要求让其他人、其他账户的 Codex 轮替继续本项目。公开 GitHub 仓库、可复现文档、明确的当前验收状态和不含凭据的证据是交接载体。其他账户需自行使用其 GitHub 权限/fork 与本机环境；原账户的密钥和原始数据不随仓库转移。
- 用户已在 Featherless 登录，但未授权购买订阅或进行生产付费调用；免费 SimpleJev Demo 限额三次已经全部使用。当前建议不购买套餐。将来如确需生产 API，Developer 是可用于 API 的方案，Chat 方案只供购买者交互聊天。
- GitHub CLI 现已认证为 `LN6666`，公开仓库发布已获用户明确授权。发布后的地址及实际 CI 状态以仓库和 `execution/STATE.md` 为准。
- 已发布到 https://github.com/LN6666/CiviFlux ，默认分支 `main`，可供其他账户克隆；首次 Actions 检查通过。公开源码交接不等于完整 v1 release 或模型付费联调授权。

## 扩展前瞻验证事件池 — 2026-09-24

- 用户要求不局限于 Helsinki，核查欧盟城市与伊斯坦布尔的 F1 和其他大型活动日期，并设置提醒。候选及官方来源见 `docs/EVENT_VALIDATION_WATCHLIST.md`。优先选择明确封路且可能取得独立运营/交通观测的活动；赛事日期不是实际道路限制或预测准确性证据。
- 当前 Codex 任务已创建并启用每周一的“CiviFlux 大型事件验证提醒” heartbeat（automation id `civiflux`），仅在临近准备/收集窗口、官方变化或需要用户行动时通知。Berlin 2026-09-27 距离很近，赛前冻结须立即处理，不能等待下周周期提醒。
- 阿姆斯特丹 2026-10-17/18、伊斯坦布尔 2026-11-01 等为前瞻验证候选。NDW 历史观测和伊斯坦布尔传感器数据的事件路段覆盖、获取权限与许可尚未确认；不能将 Google Maps 流量或路线内容导入当前 MapLibre/OSM 包。

## 城市 KG 与验证优先级 — 2026-09-25

- 用户明确要求**先优先做城市本体和知识图谱，按大型活动时间排序**；一般工程扩展暂缓。Berlin 9 月 26–27 日马拉松和 Baku 9 月 24–26 日 F1 因临近先处理。不同城市/事件的快照、时区、公告、实际操作和验证结果不得混用。
- Berlin 的已开始限制只能作为“已知起始状态”的候选；未开始的 9 月 26 日限制可在开始前冻结**增量条件探针**。公告早于预测并不破坏事前性，但公告不是实际执行或独立交通结果。机器道路映射未经人工复核，探针不是历史准确率。
- Baku 必须使用 **2026 正文**的官方页面；部分官网搜索结果在 2026 站点外壳下仍是 2024/2025 正文。Baku 封路 9 月 19/20 日已开始，不能追认事前封路预测。先审计 V1a/V1b 来源与城市图，再寻找独立 V2/V3 结果。
- 当前 Berlin、Baku 公共数据抓取、CityPack/KG 构建和离线探针**都不需要 Featherless 订阅**。免费 demo 三次已用完；生产 paid API 仍未获授权。若后续必须付费，先向用户说明用途、调用上限和预计费用；不得自动购买或调用。
