# 当前执行状态 / Handoff state

更新：2026-09-24。状态：**IMPLEMENTED_PARTIAL_ACCEPTANCE**。不能把手交包的 66 项 reference tests 当作产品验收。

## 当前权威入口

1. `execution/USER_DECISIONS.md`：用户决定优先于旧 pack；Qwen 必须 API；当前 System-One 为 Featherless SimpleJev；暂不付费；GitHub 公开仓库已授权。
2. `README.md` → `docs/index.md` → `docs/CURRENT_ARCHITECTURE.md` / `docs/CURRENT_RUNBOOK.md`。
3. `docs/ARCHITECTURE_GUARDRAILS.md`：用户指定第 9–20 节风险对应的工程约束。
4. `evidence/current_product_release.json`：严格 release gate；尚未完成的 gate 不伪造 PASS。

## 已落地

- Python application/domain/adapters 分层；唯一 ontology 注册表与生成契约；Action 事务、重放、来源和时间约束。
- Directed turn routing、真实 SUMO adapter、operational / dependency-evidence 图分离、可验证的稀疏 personalized PageRank。
- 本地 API、后台运行/取消、对象视图和可下载 evidence bundle；Lit 插件支持 MapLibre 与无地图宿主。
- 已下载 HSL/OSM/GTFS 数据，构建 Helsinki citypack；真实城市道路与火灾当前网络 what-if 已运行。
- SimpleJev 远程 typed classifier 适配器；真实免费 demo 与 toy/Helsinki 图应用已通过限定范围验证（免费请求3次，付费0次）；生产 paid 调用关闭。普通 Qwen chat API 仅为可选备用接口，不能替代 SimpleJev 验收。
- 固定场景消融、独立路由 oracle、PPR 数值 oracle、ontology 回归检查、核心性能与外部开源系统的受限 smoke。

## 本轮仍在收尾

- 最终 Python 检查207通过（包括66项原参考检查）；浏览器6通过。干净检出、冻结依赖安装和隔离 wheel 运行均通过（7d217b8）。
- 同步 release manifest 与实际检查结果，保留用户推迟的 gate。
- GitHub 已认证为 LN6666；当前正准备已授权的公开仓库发布。

## 明确缺口

- 生产 SimpleJev paid 调用：DEFERRED_USER；免费 demo 必须单列证据，不能冒充生产验收。
- 独立专家语义标签/模型校准、人工入口与事件几何核验：未完成；不报告校准概率或历史预测精度。
- 原始城市数据保存在 ignored data/raw 与 citypack 目录；公开仓库包含获取/构建脚本、来源、许可证和校验值，不包含凭据或大型原始数据。
- Docker daemon 当前不可用；Docker 构建/镜像 digest 固定尚未验证。native local 运行与容器部署分开。

## 接手操作

先读用户决定与本文件，再看 git status 和实际 evidence。使用 Python3.12、uv.lock、Node22 与 web/package-lock.json。运行 `make bootstrap test-fast test-data test-sumo build-web`；浏览器测试另运行 `make test-browser`。禁止自动下载模型或启用 paid API；`.env` 不得提交。旧开发缓存/运行保留，发生 ontology 输入变化应创建新运行，不改写旧哈希。
