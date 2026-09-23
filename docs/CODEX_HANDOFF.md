# CiviFlux 轮替交接：给下一位 Codex

这是当前项目的**执行入口**。先读本文件及[用户要求对照](USER_REQUIREMENTS_TRACE.md)，再看 [`execution/STATE.md`](../execution/STATE.md)、[`execution/ACCEPTANCE.md`](../execution/ACCEPTANCE.md) 和 [`evidence/current_product_release.json`](../evidence/current_product_release.json)。旧 `MASTER_PLAN.md`、编号设计文档、旧 prompt 和 `evidence/product_release.json` 是导入时的历史基线，不能覆盖当前用户决定或运行状态。

仓库：[LN6666/CiviFlux](https://github.com/LN6666/CiviFlux)，公开。所有人可读；其他账号贡献时 fork 或创建有权限的分支并提交 PR，由仓库维护者审核。不得假定自己拥有原始账号的 Featherless、GitHub 或本机凭据，也不能自动继承本次 Codex 会话的 goal 状态。`main` 是集成线；开发分支使用 `codex/` 前缀。先读 `git status`、最近提交和 CI，不重做已完成实验，也不改写共享历史。

**交接锚点：**`main` 的已集成起点为 `7a97e22`；本轮 42/10 验收账本、220 项 Python/10 项浏览器证据和负面 Helsinki 边界结果位于待审的 [PR #1](https://github.com/LN6666/CiviFlux/pull/1)（`codex/close-independent-v1-gates`）。接手者先看 PR 的实际状态与 CI；只有合并后才把其中内容当作 `main`。即使 PR 尚未合并，本文件在 `main` 的旧版已提供基本接手步骤，PR 给出最新证据。

## 新账户的第一步

1. 在自己的机器执行 `git clone https://github.com/LN6666/CiviFlux.git`，在 Codex 中把克隆出的 `CiviFlux` 目录作为项目打开。公开仓库可匿名克隆；提交 PR 时才需要自己的 GitHub 身份或 fork。接手正在审查的改动时也查看[开放的 PR](https://github.com/LN6666/CiviFlux/pulls)，不要以为未合并分支已经在 `main`。
2. 依次读本文件、[用户要求对照](USER_REQUIREMENTS_TRACE.md)、[当前状态](../execution/STATE.md)、[验收清单](../execution/ACCEPTANCE.md)、[用户决定](../execution/USER_DECISIONS.md)；然后看 `git status`、`git log -1` 和仓库最新 [CI](https://github.com/LN6666/CiviFlux/actions)。历史 Master Plan 只在细节争议时查阅。
3. 将本文件末尾的“新会话起始提示”发给新 Codex，并说明要进入 goal 模式。当前账户的 goal 状态不会跨账户复制；新代理应以 54 项目标和实际 release gate 继续，勿把已通过内容重新标为待办。
4. 配好 Python 3.12、`uv` 0.11.23、Node 22 后运行 `make bootstrap`；先运行与所改模块相关的测试，再按[运行手册](CURRENT_RUNBOOK.md)运行需交付的检查。初始 clone 不含 ignored 城市原始数据；需要 Helsinki 案例时按[数据说明](../data/README.md)获取和重建。
5. 无仓库写权限时在自己的 GitHub 账户 fork，开 `codex/` 主题分支并向受保护的 `main` 发 PR；有写权限也按[版本规则](VERSIONING.md)执行。`core` 检查与代码所有者审查是非管理员合并门槛。PR 说明须注明目标 ID、变更、命令/退出码、证据及剩余限制。不要复制原账户的本地 `.env`、Key、运行缓存或把线上模型调用当作 CI 默认步骤。

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
- 当前实证：完整 Python 检查 220 passed（含 66 项原参考检查与新增 SUMO/SBOM 专项），浏览器套件 10 passed。真实 SUMO、真实 Helsinki what-if、48 场景/192 运行的 A0/A1/A2/A5 工程消融和独立 oracle 留证据。免费 SimpleJev 共 3 请求，0 付费；真实评分经内容寻址缓存应用到 toy 与 Helsinki，物理 facts 保持不变。**这不构成专家校准、历史预测或生产订阅通过。**
- 本轮独立证据：更大 Helsinki 路网与原案例的固定 OD 比较显示**边界不稳定**；多封路环路反例、Web 反复挂载/取消和软件 SBOM 已补证。详见[验收清单](../execution/ACCEPTANCE.md)和各自 evidence。SBOM 跟踪的是本机原生文件；其他系统要本机生成并验证自己的清单。
- 干净检出：[`evidence/wp7/clean_checkout.json`](../evidence/wp7/clean_checkout.json) 记录冻结依赖、toy 运行、wheel 构建与隔离导入 PASS；首次仅离线缓存缺少 SUMO wheel 的记录也保留。Docker daemon 本机不可用，容器部署仍须另验。
- 状态与证据：[`evidence/README.md`](../evidence/README.md) 提供索引；`make release-check` 在必要 gate 未完成时**应返回非零**，这是诚实结果。不要将 CI 测试通过写成 `engineering_complete=true`。

## 后继工作按依赖推进

1. 对照 [`execution/ACCEPTANCE.md`](../execution/ACCEPTANCE.md) 的 54 目标与当前 release manifest；只修复真正缺失的 v1 条款。先确认[开放 PR](https://github.com/LN6666/CiviFlux/pulls) 与 `main` 的差异，再决定起始提交。新实现须附测试、数据来源和客观证据，更新同一目标状态。
2. 用户/领域专家才能完成的道路方向、事件几何、设施入口与关系标签核验应显式列为待输入，不要用 LLM 充当独立标签。可继续收集公开来源与缩小不确定映射，但不将机器候选晋升为已核验。
3. A3/A4 付费生产与人工校准在用户改变决定前继续 `DEFERRED_USER`。免费 demo 当前三次预算已经用尽，不能沿用旧 budget ID 再发请求。历史交通结果没有独立观测，不给出事故/风险概率。
4. 在可用的 Linux/Docker 环境验证容器构建、固定基础镜像 digest 与最小权限；记录实际命令/版本/输出。已验证的 macOS native 安装不能替代这一条。真实 Helsinki 当前小边界的 OD 对外圈不稳定，必须重新选取正式边界再升级城市案例主张。
5. 未来贡献按 [`VERSIONING.md`](VERSIONING.md) 和 [`CONTRIBUTING.md`](../CONTRIBUTING.md) 进入 PR。GitHub Actions 是公开仓库的共享检查；CI 初次运行失败要基于日志做局部修复，不跳过失败 gate。

## 新会话可以直接使用的起始提示

> 请进入 goal 模式，继续公开仓库 `LN6666/CiviFlux` 的 Road & Fire GIS v1。先读取 `docs/CODEX_HANDOFF.md`、`docs/USER_REQUIREMENTS_TRACE.md`、`execution/STATE.md`、`execution/ACCEPTANCE.md`、`execution/USER_DECISIONS.md` 和 `evidence/current_product_release.json`，检查当前 Git/CI 与开放 PR。沿当前未完成目标做最小有证据的实现与修复，完成相应测试、文档和 PR。Featherless SimpleJev Qwen3.8-27B 只通过托管 API；免费 Demo 三次已用完，生产付费未经授权，预算为零，不本地部署模型。保持本体只服务 v1、物理 facts 与语义 attention 分离、不能将候选数据或模型评分当成核验事实。更大 Helsinki 路网检查已发现当前案例边界不稳定。不要重跑未受变更影响的冻结实验；不能完成的外部 gate 如实标记并继续独立工作。

这是一份项目工作说明，不代替来自当前用户的新指示。接手者应以本次任务中的用户要求为准，保留已作出的授权和费用边界。
