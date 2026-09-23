# 当前执行状态 / Handoff state

更新：2026-09-24。状态：**IMPLEMENTED_PARTIAL_ACCEPTANCE**。不能把手交包的 66 项 reference tests 当作产品验收。

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
- [PR #2](https://github.com/LN6666/CiviFlux/pull/2) 包含正式边界、历史预检、Linux 容器修复和发布证据的修订绑定。该分支的 54 项账本为 **44 PASS / 8 PARTIAL / 1 DEFERRED_USER / 1 BLOCKED_EXTERNAL**。严格 release manifest 虽保存 8 个历史 `PASS` 记录，但受控代码/测试/构建输入此后已变化，其中 7 个现被检出为 stale，另 1 个引用的临时 CI merge commit 不在当前 Git 历史中；它们**不是当前修订的有效发布 PASS**。Qwen 与消融 2 个 `DEFERRED_USER`、真实城市 1 个 `BLOCKED_EXTERNAL`，`engineering_complete=false`；`make release-check` 正确返回非零。[最新代码 CI](https://github.com/LN6666/CiviFlux/actions/runs/35909793638) 的 `core` 与 `container` 均通过，包括 Python/数据/SUMO/安全检查、Web 构建和浏览器测试；CI 通过不自动重签 release manifest。三轮容器失败及通过的原始证据均保留。
- [PR #3](https://github.com/LN6666/CiviFlux/pull/3) 单独修补 SimpleJev 缓存契约、冻结响应来源和旧本地部署文档，并隔离过时的本地 Qwen 交接指令；63 项相关本地测试及最新 `core` CI 通过。[PR #4](https://github.com/LN6666/CiviFlux/pull/4) 保存 Helsinki Service Map 官方单位/入口、冻结 HSL OSM 建筑/服务路与有向道路的**候选**审查报告；Aurora 入口的官方建筑编号和最近 OSM 建筑冲突，近邻服务路导入边无 passenger/emergency 权限。R1 公告映射已绑定来源卡片，端点/方向/日期精度变化会拒绝静默复用。`make test-data` 本地 32 项通过；以 PR 最新 CI 为准。[PR #5](https://github.com/LN6666/CiviFlux/pull/5) 修复陈旧物理结果进入 KG 投影，且派生 link 引用实际路/设施/路线来源、共享 OD 的依据与图哈希对记录顺序稳定；42 项图专项及 192 项快速测试通过，[最新 `core` CI](https://github.com/LN6666/CiviFlux/actions/runs/35907213668) 通过。三者均从当前 `main` 建分支，**尚未包含 PR #2 的 `container` 工作流**。
- [草稿 PR #6](https://github.com/LN6666/CiviFlux/pull/6) 在隔离分支合并 PR #2–#5，供 Linux CI 检查模块组合；冻结 SimpleJev 720 次 permutation 对照仅因新增 `physical_context_hash` 而离线刷新整份物理事实哈希，图/PPR 结果不变。该草稿不是 v1 发布或代替源 PR 审查；检查状态以 PR checks 为准。
- `main` 保护要求 `core`、`container`、代码所有者审查和线性历史，禁止强推/删除。[PR #2–#5](https://github.com/LN6666/CiviFlux/pulls) 均仍开放且需审查；当前 `CODEOWNERS` 仅有 PR 作者 `@LN6666`，作者不能自行批准。PR #2 合并后，须更新 PR #3/#4/#5 到新 `main` 并取得 `container` 检查，不能把只有 `core` 绿色写成可合并或已发布。

## 明确缺口

- 生产 SimpleJev paid 调用：DEFERRED_USER；免费 demo 必须单列证据，不能冒充生产验收。
- 独立专家语义标签/模型校准、人工入口与事件几何核验：未完成；不报告校准概率或历史预测精度。
- 原始城市数据保存在 ignored data/raw 与 citypack 目录；公开仓库包含获取/构建脚本、来源、许可证和校验值，不包含凭据或大型原始数据。
- 扩大 Helsinki 当前路网后，同一批固定候选 OD 在内圈→外圈出现道路 3 处、火灾 8 处阶段差异；第一外圈→第二外圈该批 48 个目标的 96 个阶段在 1 秒阈值下无差异。第一外圈仅作为此批目标的案例边界；3 个入口无法配对，2 个会重新吸附，不升级成全城/历史结论。证据见 `evidence/wp2/helsinki_boundary_sensitivity.json` 与 `helsinki_formal_boundary_case.json`。
- 历史事件回测预检显示事件公告机器映射尚未人工接受、火灾实际警戒区未知、事发时网络和独立实测结果缺失。按 `docs/HISTORICAL_BACKTEST_PROTOCOL.md` 分层验收，数值预测仍 `NOT_VALIDATED`。
- PR #4 的官方服务地图只使 Tölö gymnasium 得到单位身份候选。Aurora 官方 unit 26110 写 `rak. 15`，入口 21577 距 OSM `Aurora 14` 轮廓 1.98 m；最近服务路导入边不允许 passenger/emergency。7 个已检查的官方入口点及道路几何、导入权限和转弯覆盖可供人工审查，但入口所属设施、实际建筑到道路连接及历史通行均未验证，G102/G205 仍 `PARTIAL`。R1 公告来源卡片与机器候选映射现在逐事实关联，但人工有向边核验仍为 0，G104/G603 仍 `PARTIAL`。市政年度平均交通量不能替代 2026 年 5 月事件小时的独立观测；G605 仍 `BLOCKED_EXTERNAL`。
- 本机 Docker daemon 不可用；PR #2 的 GitHub Linux 已完成固定基础镜像构建、本地镜像内容 digest 检查，以及无网络、只读容器中的真实 API/export/SUMO smoke。该 digest 不是已发布 registry 的 `RepoDigest`。G701 可在此受限范围内标 PASS；它不构成历史城市预测或生产模型验收。

## 接手操作

先读用户决定与本文件，再看 git status、[开放 PR](https://github.com/LN6666/CiviFlux/pulls) 和实际 evidence。使用 Python3.12、uv.lock、Node22 与 web/package-lock.json。运行 `make bootstrap test-fast test-data test-sumo security-check build-web`；浏览器测试另运行 `make test-browser`。跨平台核对已发布 SBOM 用 `make sbom-check`；本机原生清单另用 `make sbom-host-check`。禁止自动下载模型或启用 paid API；`.env` 不得提交。旧开发缓存/运行保留，发生 ontology 输入变化应创建新运行，不改写旧哈希。
