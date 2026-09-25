# 当前执行状态 / Handoff state

更新：2026-09-25 UTC。状态：**IMPLEMENTED_PARTIAL_ACCEPTANCE**。不能把手交包的 66 项 reference tests 当作产品验收。

## 最新工作树检查点：城市 KG 与赛事验证准备

当前开发线为 draft [PR #7](https://github.com/LN6666/CiviFlux/pull/7) 的 `codex/directed-mapping-review`。下文按提交记录列出的早期 CI/哈希是**历史检查点**；新增 Berlin/Baku 城市图代码在更新的 CI 通过和 release manifest 重绑定前，不继承旧代码树的 PASS。新数据与结果的范围如下：

- Berlin 的固定 Geofabrik OSM 源 SHA-256 为 `ff4ac9a01c7d7c13dc3a9a47e4a5031152c82cfed36720fe2a1bf99543fb1a76`；[城市 KG 审计](../evidence/events/berlin-2026-city-kg-audit.json)记录 153,264 条有向道路、239,430 条转向关系和 153,900 个 ontology objects。9 月 21 日官方公告仅有 2 段街道经算法提出 37/35 条候选有向边，均为 `CANDIDATE_UNREVIEWED`；不能宣称完整封路网络。
- Berlin [增量条件探针](../evidence/events/berlin-2026-incremental-pre-onset-probe.json)于 `2026-09-25T18:20:40Z` 冻结，早于 26 Sep 07:00 CEST 的**计划**封路起点。相同当前网络、OD 与已知起始候选下，两组东西向 OD 在新增候选封路时不可达，北侧对照 OD 不变。此敏感性是未审阅候选映射上的自由流路径结果；真实道路运行、其他先前封路、需求/拥堵、边界外绕行和独立观测均未验证，不能列为 V2/V3 预测准确性。
- Baku 已下载 18 Sep 2026、首批公告限制开始前的 [Geofabrik OSM](https://download.geofabrik.de/asia/azerbaijan.html)（46,189,332 bytes；SHA-256 `5134c55378dda62dfe4257b6aa7eec06fe9c67594f7e578bcd6186fbaac5c363`）；[城市 KG 审计](../evidence/events/baku-2026-city-kg-audit.json)记录 74,289 条有向道路、130,326 条转向关系和 75,095 个 ontology objects。官方 2026 赛事交通公告与 AYNA 公交改线以[来源事实卡](../data/event_cases/baku-f1-2026-source-facts.json)固定；[可行性审计](../docs/BAKU_2026_F1_DATA_FEASIBILITY.md)区分 V1a 计划事实与缺失的 V1b 人工映射、V2 实际运营和 V3 数值观测。巴库封路 19/20 Sep 已开始，不能追认事前预测。
- 本机执行 `make test-fast test-data test-outcomes test-sumo security-check`：fast 210、当次 data 51 PASS/1 SKIP、outcomes 7、SUMO 11、安全 20，通过；加入 freeze guard 后复跑 `make test-data` 为 **53 PASS/1 SKIP**。data 的 1 项跳过因本开发工作树未带 ignored Helsinki 城市包，不能视为发布所需真实数据验证通过。城市原始 PBF 与大型 CityPack/KG 保持 ignored，本仓库只提交脚本、小型来源卡和哈希证据。
- 上述城市构建和离线验证**不需要 Featherless 订阅**；免费 demo 三次已耗尽，付费生产调用继续 `DEFERRED_USER`。如将来必须付费，先告知用户用途、调用限额和估算费用。

## 当前权威入口

1. `execution/USER_DECISIONS.md`：用户决定优先于旧 pack；Qwen 必须 API；当前 System-One 为 Featherless SimpleJev；暂不付费；GitHub 公开仓库已授权。
2. `README.md` → `docs/index.md` → `docs/CURRENT_ARCHITECTURE.md` / `docs/CURRENT_RUNBOOK.md`。
3. `docs/ARCHITECTURE_GUARDRAILS.md`：用户指定第 9–20 节风险对应的工程约束。
4. `docs/CODEX_HANDOFF.md` 与 `docs/USER_REQUIREMENTS_TRACE.md`：其他账户的执行入口和本次用户要求逐项落实位置。
5. `evidence/current_product_release.json`：严格 release gate；尚未完成的 gate 不伪造 PASS。

## 已落地

- Python application/domain/adapters 分层；唯一 ontology 注册表与生成契约；Action 事务、重放、来源和时间约束。
- Directed turn routing、真实 SUMO adapter、operational / dependency-evidence 图分离、可验证的稀疏 personalized PageRank。
- 本地 API、后台运行/取消、对象视图和可下载 evidence bundle；Lit 插件支持 MapLibre 与无地图宿主。
- 已下载 HSL/OSM/GTFS 数据，构建 Helsinki citypack；真实城市道路与火灾当前网络 what-if 已运行。
- SimpleJev 远程 typed classifier 适配器；真实免费 demo 与 toy/Helsinki 图应用已通过限定范围验证（免费请求3次，付费0次）；生产 paid 调用关闭。普通 Qwen chat API 只可用于可选语言接口，不能作为 classifier 备用或替代 SimpleJev 验收。
- 固定场景消融、独立路由 oracle、PPR 数值 oracle、ontology 回归检查、核心性能与外部开源系统的受限 smoke。

## 已发布与核验

- [公开仓库](https://github.com/LN6666/CiviFlux) 的 `main` 当前为 `776bf2c`（[PR #1](https://github.com/LN6666/CiviFlux/pull/1) 已合并），[main CI](https://github.com/LN6666/CiviFlux/actions/runs/35895921643) 通过。`main` 自己的 54 项账本仍为 **42 PASS / 10 PARTIAL / 1 DEFERRED_USER / 1 BLOCKED_EXTERNAL**；其旧 `GATE-REPRODUCE` 仍为 `BLOCKED_ENVIRONMENT`，不能用开放 PR 的证据替换主分支状态。
- [PR #2](https://github.com/LN6666/CiviFlux/pull/2) 包含正式边界、历史预检和 Linux 容器修复。该分支的 54 项账本为 **44 PASS / 8 PARTIAL / 1 DEFERRED_USER / 1 BLOCKED_EXTERNAL**；严格 release manifest 中 8 个 gate PASS，Qwen 与消融 2 个 `DEFERRED_USER`、真实城市 1 个 `BLOCKED_EXTERNAL`，`engineering_complete=false`。[run 35910119227](https://github.com/LN6666/CiviFlux/actions/runs/35910119227) 的 `core` 与 `container` 均通过，包括分组 Python/数据/SUMO/安全检查、Web 构建和浏览器测试。三轮容器失败及通过的原始证据均保留。
- [PR #3](https://github.com/LN6666/CiviFlux/pull/3) 单独修补 SimpleJev 缓存契约、冻结响应来源和旧本地部署文档，并隔离过时的本地 Qwen 交接指令；63 项相关本地测试及最新 `core` CI 通过。[PR #4](https://github.com/LN6666/CiviFlux/pull/4) 保存 Helsinki Service Map 官方单位/入口、冻结 HSL OSM 建筑/服务路与有向道路的**候选**审查报告；Aurora 入口的官方建筑编号和最近 OSM 建筑冲突，近邻服务路导入边无 passenger/emergency 权限。R1 公告映射已绑定来源卡片，端点/方向/日期精度变化会拒绝静默复用。`make test-data` 本地 32 项通过；以 PR 最新 CI 为准。[PR #5](https://github.com/LN6666/CiviFlux/pull/5) 修复陈旧物理结果进入 KG 投影，且派生 link 引用实际路/设施/路线来源、共享 OD 的依据与图哈希对记录顺序稳定；42 项图专项及 192 项快速测试通过，[最新 `core` CI](https://github.com/LN6666/CiviFlux/actions/runs/35907213668) 通过。三者均从当前 `main` 建分支，**尚未包含 PR #2 的 `container` 工作流**。
- [PR #6](https://github.com/LN6666/CiviFlux/pull/6) 是仍为 draft 的组合验证分支，把 #2–#5 一起放到 Linux CI 中运行；[run 35909918574](https://github.com/LN6666/CiviFlux/actions/runs/35909918574) 的 `core` 与 `container` 均通过，包括浏览器测试。它并非已合并 release，也不能让早期 release manifest 的 PASS 自动沿用到不同 tree；当前严格 release-check 会拒绝失效哈希。CI 的数据套件缺少 ignored 原始 CityPack，因此有 1 项真实数据测试跳过。
- [PR #7](https://github.com/LN6666/CiviFlux/pull/7) 是基于 #6 的 draft：补上独立道路映射审阅表校验与样本外边界探针；审阅表绑定公告来源卡、机器候选报告/CSV、地图与几何的哈希，未有真人提交，实际接受数仍为 0。历史预检忽略机器文件中自报的人工接受、实际执行和历史路网标志，V1b 保持 `NOT_VALIDATED`。正式案例选定的 Helsinki 外圈包约 26 MiB，超过 Web 上传限额；现在本地 API 仅在文件哈希、OSM 来源与案例报告相符时直接登记，包级 warning 列出 48 个固定候选入口、3 个排除入口及 2 个会重新吸附的原生入口，绝不把此范围扩写为全城或历史有效性。工作包和执行文档已统一指向 hosted SimpleJev，发布检查现把 `.dockerignore` 计入版本绑定输入。本机组合核验：快速测试 206、数据测试带真实 CityPack 50（无 CityPack 为 49+1 skip）、outcomes 6、SUMO 11、安全 19、SBOM/Web 构建通过；外圈包经 API 真正创建并完成一次分析运行，PPR 收敛，分类器出网关闭；干净 Git 导出的离线安装和隔离 wheel smoke 通过。本机 Playwright 缺 Chromium 可执行文件，因此浏览器套件由 [run 35914411202](https://github.com/LN6666/CiviFlux/actions/runs/35914411202) 的 Linux `core` 检查完成；同次 `container` 检查也通过。该轮基线代码为 `3260ccd`，不是已合并 release。
- [PR #7](https://github.com/LN6666/CiviFlux/pull/7) 后续代码提交 `0ef38d7` 将正式外圈案例的范围说明和报告 SHA-256 贯穿包列表、分析结果及导出 ZIP；旧工作区中未绑定当前证据的结果会拒绝读取、导出及幂等复用，要求重新运行，不改写旧结果。正式案例报告本身现是 release 版本绑定输入。Web 注意力页改为每页 100 条并支持全量搜索；完整记录仍在结果及 ZIP。真实外圈浏览器复测见 [限定范围证据](../evidence/wp5/helsinki_outer_browser_smoke.json)：151 个 OD、27,108 条注意力记录，切换注意力页 59 ms、100 行，无出网请求或浏览器错误；此为一次本机 headless smoke，非跨设备性能保证。[GitHub run 35917742069](https://github.com/LN6666/CiviFlux/actions/runs/35917742069) 在该代码树的 PR HEAD `0fa00f8` 上 `core` 与 `container` 均通过：快速 206、数据 49+1 skip（CI 未提供 ignored 城市原包）、outcomes 6、SUMO 11、安全 20、浏览器 11。生产 SimpleJev/完整消融仍按用户决定暂停；历史/人工城市核验仍缺，PR 仍是 draft，不能标完整发布。
- PR #7 再以代码提交 `ada0475` 修复当前树的干净检出脚本：离线复现安装实际 wheel，不再因 editable 构建缺少 `editables` 失败。[本机报告](../evidence/wp7/clean_checkout_ada_offline.json) 的 10 个阶段均 PASS（使用已有冻结依赖缓存）；[GitHub run 35919129902](https://github.com/LN6666/CiviFlux/actions/runs/35919129902) 对相同受控代码树的 `core` 和 `container` 均 PASS，11 项浏览器测试无跳过/意外失败，见 [CI 摘要](../evidence/wp7/ci_run_35919129902.json)。本机临时链接 ignored Helsinki 当前快照运行 `make test-data` 为 [50 PASS](../evidence/wp7/current_data_test_ada.json)，链接已移除。当前 strict release manifest 的 8 个非付费 gate 重新绑定这棵代码树并通过校验；付费 classifier、完整消融仍 `DEFERRED_USER`，真实城市独立验证仍 `BLOCKED_EXTERNAL`，`engineering_complete=false`。
- `main` 保护要求 `core`、`container`、代码所有者审查和线性历史，禁止强推/删除。[PR #2–#5](https://github.com/LN6666/CiviFlux/pulls) 均仍开放且需审查；当前 `CODEOWNERS` 仅有 PR 作者 `@LN6666`，作者不能自行批准。PR #2 合并后，须更新 PR #3/#4/#5 到新 `main` 并取得 `container` 检查，不能把只有 `core` 绿色写成可合并或已发布。

## 明确缺口

- 生产 SimpleJev paid 调用：DEFERRED_USER；免费 demo 必须单列证据，不能冒充生产验收。
- 独立专家语义标签/模型校准、人工入口与事件几何核验：未完成；不报告校准概率或历史预测精度。
- 原始城市数据保存在 ignored data/raw 与 citypack 目录；公开仓库包含获取/构建脚本、来源、许可证和校验值，不包含凭据或大型原始数据。
- 扩大 Helsinki 当前路网后，同一批固定候选 OD 在内圈→外圈出现道路 3 处、火灾 8 处阶段差异；第一外圈→第二外圈该批 48 个目标的 96 个阶段在 1 秒阈值下无差异。第一外圈仅作为此批目标的案例边界；3 个入口无法配对，2 个会重新吸附，不升级成全城/历史结论。证据见 `evidence/wp2/helsinki_boundary_sensitivity.json` 与 `helsinki_formal_boundary_case.json`。
- 固定哈希规则在每个象限另选 2 个非原场景起点，共 8 个共享的 passenger 道路节点，再对相同 48 个原候选入口比较外圈/更远圈：道路和火灾各 384 OD、768 个 baseline/event 阶段比较，状态及超过 1 秒的时间差均为 0；可达路径未改变，可达时间最大绝对差 0.868 秒。这个 holdout 只针对同一当前 OSM 快照的机器起点，未验证设施入口、真实 OD、历史事件或全城收敛；见 `evidence/wp2/helsinki_boundary_holdout_probe.json`。
- 历史事件回测预检显示事件公告机器映射尚未人工接受、火灾实际警戒区未知、事发时网络和独立实测结果缺失。按 `docs/HISTORICAL_BACKTEST_PROTOCOL.md` 分层验收，数值预测仍 `NOT_VALIDATED`。
- R1 人工审阅交接由 `scripts/road_mapping_review.py` 生成空表并校验提交记录；代码只核对来源、候选完整性与自述字段，不能证明审阅者身份、真实封路时段或历史路网。历史预检不接受机器文件中的运行/路网验证布尔值替代独立证据，不会因为填表而变为历史回测通过。
- PR #4 的官方服务地图只使 Tölö gymnasium 得到单位身份候选。Aurora 官方 unit 26110 写 `rak. 15`，入口 21577 距 OSM `Aurora 14` 轮廓 1.98 m；最近服务路导入边不允许 passenger/emergency。7 个已检查的官方入口点及道路几何、导入权限和转弯覆盖可供人工审查，但入口所属设施、实际建筑到道路连接及历史通行均未验证，G102/G205 仍 `PARTIAL`。R1 公告来源卡片与机器候选映射现在逐事实关联，但人工有向边核验仍为 0，G104/G603 仍 `PARTIAL`。市政年度平均交通量不能替代 2026 年 5 月事件小时的独立观测；G605 仍 `BLOCKED_EXTERNAL`。
- 本机 Docker daemon 不可用；PR #2 的 GitHub Linux 已完成固定基础镜像构建、本地镜像内容 digest 检查，以及无网络、只读容器中的真实 API/export/SUMO smoke。该 digest 不是已发布 registry 的 `RepoDigest`。G701 可在此受限范围内标 PASS；它不构成历史城市预测或生产模型验收。
- PR #7 早期 `0fa00f8` 的本机原生离线 clean-checkout 因缓存缺少 `sumo-data`、随后缺少 `editables` 而记录为 `BLOCKED_ENVIRONMENT`（`evidence/wp7/clean_checkout_0fa_*.json`）。提交 `ada0475` 改用非 editable wheel 安装后，在已有冻结依赖缓存的本机上对**干净 Git 导出**重新运行：离线依赖安装、toy 路由/PPR、wheel 构建及检出目录外的隔离导入均 PASS，见 [当前离线报告](../evidence/wp7/clean_checkout_ada_offline.json)。这证明当前本机缓存环境可复现，不能推断全新机器无需预置依赖缓存；生产部署与历史城市结果仍未验证。

## 接手操作

先读用户决定与本文件，再看 git status、[开放 PR](https://github.com/LN6666/CiviFlux/pulls) 和实际 evidence。使用 Python3.12、uv.lock、Node22 与 web/package-lock.json。运行 `make bootstrap test-fast test-data test-sumo security-check build-web`；浏览器测试另运行 `make test-browser`。跨平台核对已发布 SBOM 用 `make sbom-check`；本机原生清单另用 `make sbom-host-check`。禁止自动下载模型或启用 paid API；`.env` 不得提交。旧开发缓存/运行保留，发生 ontology 输入变化应创建新运行，不改写旧哈希。
