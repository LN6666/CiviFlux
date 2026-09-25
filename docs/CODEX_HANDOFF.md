# CiviFlux 轮替交接：给下一位 Codex

这是当前项目的**执行入口**。先读本文件及[用户要求对照](USER_REQUIREMENTS_TRACE.md)，再看 [`execution/STATE.md`](../execution/STATE.md)、[`execution/ACCEPTANCE.md`](../execution/ACCEPTANCE.md) 和 [`evidence/current_product_release.json`](../evidence/current_product_release.json)。旧 `MASTER_PLAN.md`、编号设计文档、旧 prompt 和 `evidence/product_release.json` 是导入时的历史基线，不能覆盖当前用户决定或运行状态。本文较早提交号/CI 数字是当时的检查点；以紧接的最新检查点和实际 PR HEAD 为准。

仓库：[LN6666/CiviFlux](https://github.com/LN6666/CiviFlux)，公开。所有人可读；其他账号贡献时 fork 或创建有权限的分支并提交 PR，由仓库维护者审核。不得假定自己拥有原始账号的 Featherless、GitHub 或本机凭据，也不能自动继承本次 Codex 会话的 goal 状态。`main` 是集成线；开发分支使用 `codex/` 前缀。先读 `git status`、最近提交和 CI，不重做已完成实验，也不改写共享历史。

**交接锚点：**[PR #1](https://github.com/LN6666/CiviFlux/pull/1) 已以 squash 方式合入 `main`（集成提交 `776bf2c`）。当前 `main` 仍为 42 PASS/10 PARTIAL。[PR #2](https://github.com/LN6666/CiviFlux/pull/2) 至 [PR #5](https://github.com/LN6666/CiviFlux/pull/5) 是未合并的分项改动；draft [PR #6](https://github.com/LN6666/CiviFlux/pull/6) 组合验证这些改动，draft [PR #7](https://github.com/LN6666/CiviFlux/pull/7) 基于 #6 增加 Helsinki 有向映射审阅、范围绑定与浏览器分页，并修复离线干净检出。接手当前组合工作可用 `gh pr checkout 7`，先检查其 base/head、最新提交与 CI，再继续开发；不要把待审内容当成 `main`。

**最新工作线，25 Sep 2026 UTC：**用户现要求优先按大型活动时间建设城市 ontology/KG，并核查 Berlin Marathon 与 Baku F1 的验证可行性。[Berlin 城市图审计](../evidence/events/berlin-2026-city-kg-audit.json)和[Baku 城市图审计](../evidence/events/baku-2026-city-kg-audit.json)记录固定 OSM 来源、范围、有向道路/转向/typed links 数量与结果哈希；原始数据和大型 CityPack/KG **gitignored，不会随 Git clone 自动到达**，按 [data/README](../data/README.md)重建。Berlin 的[官方封路候选](../data/event_cases/berlin-marathon-2026-closure-candidates.json)未经人工核验；[事前冻结的条件探针](../evidence/events/berlin-2026-incremental-pre-onset-probe.json)只给出未验证候选下的自由流路径敏感性。Baku 的[2026 来源事实卡](../data/event_cases/baku-f1-2026-source-facts.json)与[可行性审计](BAKU_2026_F1_DATA_FEASIBILITY.md)显示公告充分、赛前 OSM 可得，但封路起点已过、实际运营和独立道路数值观测未核验。**不能把公告、PPR 或这些探针写成交通预测验证。** 当前本地检查结果和下一步缺口见[STATE](../execution/STATE.md)；新代码须以最新 CI 重新核验。

**最新受控检查点，26 Sep 2026 JST：**PR #7 的 `4cc4f62` 代码树已由 [Linux CI 36186049667](https://github.com/LN6666/CiviFlux/actions/runs/36186049667) 核验，`core` 与 `container` 都通过；[CI 摘要](../evidence/wp7/ci_run_36186049667.json)记录临时合并树匹配、测试数与产物哈希。Berlin 有[多方式 KG 审计](../evidence/events/berlin-2026-multimodal-kg-audit.json)和[赛前 VIZ 覆盖／对照预检](../evidence/events/berlin-2026-viz-pre-event-coverage.json)：51 条冻结预测路段中 25 条有方向一致的 VIZ 几何匹配，26 条没有；11 条可评分的重合 VIZ 路段各选出 2 条只用赛前字段匹配的对照，最小排除距离 211.2 m。GIS 图层和事件时成对额外降速算法已就绪，但仍无赛时结果。这些数值不是预测命中率或因果效应。Baku 的[步骑间接地图](BAKU_2026_INDIRECT_GIS_COMPARISON.md)含独立的 0.2 m / 15 m **假设走廊**暴露和固定合成 OD 可达性探针，可重放 Action，明确速度假设。大型原始城市包仍需按数据说明重建；步行面未纳入可路由 KG，实际步骑限制与赛时观测仍缺失。严格 release manifest 保留 2 个 `DEFERRED_USER`、1 个 `BLOCKED_EXTERNAL`，`engineering_complete=false`。

**后续受控检查点：**PR #7 的 `d2a5db0` 代码树经 [Linux CI 36187455079](https://github.com/LN6666/CiviFlux/actions/runs/36187455079) `core`、`container` 双检查通过；[回执](../evidence/wp7/ci_run_36187455079.json)核对了临时合并树、15 项浏览器测试及容器 smoke。Baku 步骑探针新增步行区域面几何交集及最近距离指标；固定 18 Sep OSM ROI 扫描 60 处，15 m 假设走廊交集为 0 处/0 m²，最近 205.48 m。保留该负结果，面仍不参与路由或 PPR。严格 release manifest 仍有 2 个 `DEFERRED_USER`、1 个 `BLOCKED_EXTERNAL`，`engineering_complete=false`。

## 新账户的第一步

1. 在自己的机器执行 `git clone https://github.com/LN6666/CiviFlux.git`，在 Codex 中把克隆出的 `CiviFlux` 目录作为项目打开。公开仓库可匿名克隆；提交 PR 时才需要自己的 GitHub 身份或 fork。接手正在审查的改动时也查看[开放的 PR](https://github.com/LN6666/CiviFlux/pulls)，不要以为未合并分支已经在 `main`。
2. 依次读本文件、[用户要求对照](USER_REQUIREMENTS_TRACE.md)、[当前状态](../execution/STATE.md)、[验收清单](../execution/ACCEPTANCE.md)、[用户决定](../execution/USER_DECISIONS.md)；然后看 `git status`、`git log -1` 和仓库最新 [CI](https://github.com/LN6666/CiviFlux/actions)。历史 Master Plan 只在细节争议时查阅。
3. 将本文件末尾的“新会话起始提示”发给新 Codex，并说明要进入 goal 模式。当前账户的 goal 状态不会跨账户复制；新代理应以 54 项目标和实际 release gate 继续，勿把已通过内容重新标为待办。
4. 配好 Python 3.12、`uv` 0.11.23、Node 22 后运行 `make bootstrap`；先运行与所改模块相关的测试，再按[运行手册](CURRENT_RUNBOOK.md)运行需交付的检查。初始 clone 不含 ignored 城市原始数据；需要 Helsinki 案例时按[数据说明](../data/README.md)获取和重建。
5. 无仓库写权限时在自己的 GitHub 账户 fork，开 `codex/` 主题分支并向受保护的 `main` 发 PR；有写权限也按[版本规则](VERSIONING.md)执行。`core`、`container` 检查与代码所有者审查是非管理员合并门槛。PR 说明须注明目标 ID、变更、命令/退出码、证据及剩余限制。不要复制原账户的本地 `.env`、Key、运行缓存或把线上模型调用当作 CI 默认步骤。

## 用户已确定的决定

1. 直接开发 Road & Fire GIS v1，强调模块解耦、本体论、知识图谱、合适的 PageRank、真实城市数据、文档与 Git 管理。
2. System-One 是 **Featherless SimpleJev 的 `featherless-ai/Qwen3.8-27B-classifier` 托管 API**。模型不得在本地部署、下载权重或以普通生成式 Qwen/原版 Jev 冒充。用户先前选择阿里云 Model Studio 国际站可用于可选语言接口，不替代这个 classifier。
3. 用户授权了最多三次**免费 Demo** 联调；已用满并留证据。付费生产调用仍被用户明确推迟；当前预算为零。任何后继不能从“用户已注册 Featherless”推断已订阅、提供 Key 或授权花费。需要注册、密钥、订阅或人工核验时告知用户；不要要求把 Key 发到聊天。当前订阅建议：暂不订阅；需要正式 API 时为 Developer 方案，非 Chat 方案。
4. 城市源数据由项目抓取与构建，不把外部当前网络 what-if 当作历史交通真值。消防边界、封路时段与设施入口的候选映射必须保持候选/假设状态，待独立核验。
5. 本体只服务当前 Road & Fire 完整闭环。对因果、校准、缓存、迁移与性能的具体约束见 [`ARCHITECTURE_GUARDRAILS.md`](ARCHITECTURE_GUARDRAILS.md)。不要为未来插件扩张通用城市标准。

## 已有实现与可复现起点

- 代码层：`core/urbanimpact/` 的契约、事务 Action、只读 Object View、有向转向路由、情景图、稀疏关系混合 PPR；`adapters/` 的 OSM/GTFS、真实 SUMO 和 SimpleJev；`api/` 的本地任务/导出；`web/` 的两个可嵌入宿主。
- 城市：Helsinki 当前数据包在构建机的 ignored `data/citypacks/helsinki-current/citypack.json`。新环境按 [`data/README.md`](../data/README.md) 与 `make citypack-fetch citypack-build case-review` 获取/构建；这是单独的公开数据下载，不需要模型 API。来源、日期、许可和 SHA 在 [`evidence/wp1/`](../evidence/wp1/)；部分来自 OSM ODbL/HSL，代码 Apache-2.0。
- 完整工程复现：Python 3.12、`uv` 0.11.23、Node 22。`make bootstrap`，然后 `make test-fast test-data test-outcomes test-sumo build-web test-browser security-check`。浏览器测试需要 `npx --prefix web playwright install chromium`。测试不会调用付费 API；CI 也将 API 预算强制为零。
- 当前实证：PR #7 的 [GitHub CI 35919129902](https://github.com/LN6666/CiviFlux/actions/runs/35919129902) 在当时代码树上 `core`、`container` 均通过，包括 206 fast、49 data + 1 skip、6 outcomes、11 SUMO、20 security、Web 构建与 11 项浏览器测试；CI 缺少 ignored 城市原包，本地用已有 Helsinki 当前快照重跑 data 为 [50 PASS](../evidence/wp7/current_data_test_ada.json)。真实 SUMO、真实 Helsinki what-if、48 场景/192 运行的 A0/A1/A2/A5 工程消融和独立 oracle 留证据。免费 SimpleJev 共 3 请求，0 付费；真实评分经内容寻址缓存应用到 toy 与 Helsinki，物理 facts 保持不变。**这不构成专家校准、历史预测或生产订阅通过。**
- 本轮独立证据：内圈→第一外圈固定 OD 出现差异；第一外圈→第二外圈对 48 个可配对目标在 1 秒阈值下稳定，已在真实 Action→路由→KG→PPR 链路重跑。另 3 个候选入口无法配对、2 个原生入口会重新吸附，所以不能推广为全城稳定。多封路环路反例、Web 重挂载/取消、软件 SBOM 和冻结模型策略的置换负对照均有证据。历史预检表明尚无可做数值回测的独立观测，见[协议](HISTORICAL_BACKTEST_PROTOCOL.md)。
- 干净检出：当前代码提交 `ada0475` 的 [本机离线报告](../evidence/wp7/clean_checkout_ada_offline.json) 记录干净 Git 导出、冻结依赖的非 editable wheel 安装、toy 路由/PPR、wheel 构建与隔离导入 PASS；使用的是**已有依赖缓存**，新机器需先获取锁定依赖，不能据此声称冷缓存离线可用。相同受控代码树的 [Linux CI 35919129902](https://github.com/LN6666/CiviFlux/actions/runs/35919129902) `core`、`container` 均通过；[证据摘要](../evidence/wp7/ci_run_35919129902.json) 记录 checkout SHA 与运行范围。镜像基于固定基础镜像与 Debian snapshot；保存的是本地构建镜像的内容 digest，**不是已发布 registry digest**。无网络只读 smoke 完成真实 API/export 和合成需求 SUMO 1.27.1。本机 Docker daemon 不可用，但 Linux CI 补齐限定范围容器证据；不代表历史城市或付费模型验收。
- 状态与证据：[`evidence/README.md`](../evidence/README.md) 提供索引；`make release-check` 在必要 gate 未完成时**应返回非零**，这是诚实结果。不要将 CI 测试通过写成 `engineering_complete=true`。

## 后继工作按依赖推进

1. 对照 [`execution/ACCEPTANCE.md`](../execution/ACCEPTANCE.md) 的 54 目标与当前 release manifest；只修复真正缺失的 v1 条款。先确认[开放 PR](https://github.com/LN6666/CiviFlux/pulls) 与 `main` 的差异，再决定起始提交。新实现须附测试、数据来源和客观证据，更新同一目标状态。
2. 用户/领域专家才能完成的道路方向、事件几何、设施入口与关系标签核验应显式列为待输入，不要用 LLM 充当独立标签。可继续收集公开来源与缩小不确定映射，但不将机器候选晋升为已核验。
3. A3/A4 付费生产与人工校准在用户改变决定前继续 `DEFERRED_USER`。免费 demo 当前三次预算已经用尽，不能沿用旧 budget ID 再发请求。历史交通结果没有独立观测，不给出事故/风险概率。
4. Linux CI 容器复现证据已保存；后续部署平台如变更基础镜像/依赖仍须重验。Helsinki 第一外圈仅覆盖本轮 48 个可配对候选目标；其余入口映射/核验完成前不可升级城市案例主张。
5. 未来贡献按 [`VERSIONING.md`](VERSIONING.md) 和 [`CONTRIBUTING.md`](../CONTRIBUTING.md) 进入 PR。GitHub Actions 是公开仓库的共享检查；CI 初次运行失败要基于日志做局部修复，不跳过失败 gate。

## 新会话可以直接使用的起始提示

> 请进入 goal 模式，继续公开仓库 `LN6666/CiviFlux` 的 Road & Fire GIS v1。先读取 `docs/CODEX_HANDOFF.md`、`docs/USER_REQUIREMENTS_TRACE.md`、`execution/STATE.md`、`execution/ACCEPTANCE.md`、`execution/USER_DECISIONS.md` 和 `evidence/current_product_release.json`，检查当前 Git/CI 与开放 PR。PR #1 已合并，之后开发分支提交须另开 PR。当前先按活动时间优先做城市 ontology/KG 和独立验证准备：Berlin 与 Baku 的固定源、候选城市图和小型证据已在 draft PR #7 工作线；大文件需重建，Berlin 候选封路待人工复核，Baku 有公告但无已核实的实际路段观测。沿当前未完成目标做最小有证据的实现与修复，完成相应测试、文档和 PR。Featherless SimpleJev Qwen3.8-27B 只通过托管 API；免费 Demo 三次已用完，生产付费未经授权，预算为零，不本地部署模型。需要订阅时先告知用户用途、上限和费用，不自动购买。保持本体只服务 v1、物理 facts 与语义 attention 分离、不能将候选数据或模型评分当成核验事实。Helsinki 第一外圈只对本轮 48 个可配对目标提供限定范围稳定性；历史数值预测尚无独立观测。不要重跑未受变更影响的冻结实验；不能完成的外部 gate 如实标记并继续独立工作。

这是一份项目工作说明，不代替来自当前用户的新指示。接手者应以本次任务中的用户要求为准，保留已作出的授权和费用边界。
