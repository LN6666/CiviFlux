# UrbanImpact / CiviFlux Road & Fire GIS v1 · Qwen System-One + Operational Ontology 完整工程方案

更新日期：2026-09-23。handoff-3-operational-ontology。

本版本在 Qwen System-One 方案上新增开放 operational ontology（Object/Link/Interface/Action/Function/Projection）与竞争比较/benchmark 规范。Palantir Foundry Ontology 仅作为公开架构思想参考，项目不依赖 Palantir。

**这是工程执行方案与参考测试，不是声称插件已经开发完成。**

## 目录

1. `README.md`
2. `AGENTS.md`
3. `docs/00_PRODUCT.md`
4. `docs/01_ARCHITECTURE.md`
5. `docs/02_DATA_CASES.md`
6. `docs/03_CONTRACTS.md`
7. `docs/04_KG_PPR.md`
8. `docs/05_QWEN_SYSTEM_ONE.md`
9. `docs/06_ROAD_FIRE_SUMO.md`
10. `docs/07_WEB_SECURITY.md`
11. `docs/08_TESTING.md`
12. `docs/09_VALIDATION_ABLATION.md`
13. `docs/10_EXECUTION.md`
14. `docs/11_RELEASE.md`
15. `docs/12_RISKS_DECISIONS.md`
16. `docs/13_JEV_TO_QWEN_MIGRATION.md`
17. `docs/14_OPERATIONAL_ONTOLOGY.md`
18. `docs/15_COMPETITIVE_BENCHMARK.md`
19. `execution/GOALS_AND_LOOPS.md`
20. `execution/ACCEPTANCE_COMMANDS.md`
21. `prompts/00_MASTER.md`
22. `prompts/01_WP0.md`
23. `prompts/02_WP1.md`
24. `prompts/03_WP2.md`
25. `prompts/04_WP3.md`
26. `prompts/05_WP4.md`
27. `prompts/06_WP5.md`
28. `prompts/07_WP6.md`
29. `prompts/08_WP7.md`
30. `prompts/09_RESUME.md`
31. `prompts/10_REPAIR.md`
32. `prompts/11_INDEPENDENT_REVIEW.md`
33. `prompts/12_REAL_WORLD_VALIDATION.md`
34. `prompts/13_ABLATION.md`
35. `prompts/14_RELEASE_REVIEW.md`
36. `prompts/15_SECURITY_AND_EGRESS.md`
37. `prompts/16_SEMANTIC_VS_PHYSICAL.md`
38. `prompts/17_ONTOLOGY_AND_BENCHMARK.md`
39. `comparison/README.md`
40. `sources/SOURCES.md`
41. `evidence/PACK_TEST_REPORT.md`

---


<!-- SOURCE FILE: README.md -->

# UrbanImpact · Road & Fire GIS v1 — Codex 工程执行包

版本：2026-09-23 / handoff-3-operational-ontology。项目名为工作名，未验证商标或包名可用性。

**本包是完整工程任务书、Codex 调度指令、数据证据登记和可执行参考测试；不是已经实现的城市插件。**
真实 Qwen System-One 请求、Helsinki 数据文件下载、SUMO 实际联调、浏览器产品验收需要在开发仓库执行；不能将随包的参考测试替代它们。

## 先做什么

1. 在新仓库根目录解压本包；已有代码时先保留现有工作、检查差异，不覆盖用户文件。根目录 `AGENTS.md` 是项目规则。
2. 将 `prompts/00_MASTER.md` 的内容交给 Codex。让它执行完整大工作包，而不是只复述方案。
3. 第一版的 System-One 不再依赖任何注册/付费 API：使用部署者本地的 **Qwen System-One backend**；第一版参考实现为 **Reflex + Qwen3.5-4B**。首次可从 Hugging Face 下载权重，正式离线部署应预取/镜像；运行时城市数据不需要出网。远程廉价 LLM 仍是可选 BYOK。
4. 按 `execution/work_packages.json` 推进 WP0–WP7；每个工作包一次交付完整纵向能力、测试、证据和可运行结果。`execution/goals.json` 是 54 项可核验目标，不是 54 次独立聊天。

## 第一版完成的定义

一个 **可嵌入 Web 的 GIS 插件**，可导入 Helsinki 路网/设施/公交数据，编辑道路限制和火灾外部影响情景，真实执行：

`Scenario → Routing / SUMO → typed temporal KG → fixed / Qwen-System-One-conditioned PPR → facts + attention + evidence → Web map / export`

固定规则、普通 PPR、Qwen-System-One-PPR 都必须存在；Qwen System-One 必须完成**真实本地 Qwen 模型推理**、进入真实投影计算并留下 model/config/calibration provenance；mock/replay 不能满足发布闸门。

**不做** QGIS 桌面插件、3D/BIM 平台、火灾 CFD、实际消防调度、个人风险画像、作者 SaaS、机构账号/协作/集群。机构自己承担服务器和运维。

## 文件导航

- `AGENTS.md`：短而强的不可越界规则。
- `docs/00_PRODUCT.md`：范围与最终验收。
- `docs/01_ARCHITECTURE.md`：模块、依赖、数据流、接口和 repo 布局。
- `docs/02_DATA_CASES.md`：Helsinki 真实事件与数据获取/分级验证。
- `docs/03_CONTRACTS.md`、`contracts/`：具体数据和 API 契约。
- `docs/04_KG_PPR.md`：图语义、PPR 数学、可比较性、防伪消融。
- `docs/05_QWEN_SYSTEM_ONE.md`：本地 Reflex/Qwen3.5 System-One 运行、校准、硬件、协议和真实联调。
- `docs/06_ROAD_FIRE_SUMO.md`：路网、消防事件边界和仿真陷阱。
- `docs/07_WEB_SECURITY.md`：Web 插件、数据本地化、安全与部署边界。
- `docs/08_TESTING.md`、`docs/09_VALIDATION_ABLATION.md`：代码、成果、真实事件、消融测试。
- `docs/10_EXECUTION.md`：大步推进、六个有停止条件的 loop、token 预算。
- `docs/11_RELEASE.md`：可执行发布闸门与证据要求。
- `docs/12_RISKS_DECISIONS.md`：技术决策与风险处置。
- `docs/13_JEV_TO_QWEN_MIGRATION.md`：从 closed Jev 依赖迁移到本地 Qwen System-One 的变更清单。
- `docs/14_OPERATIONAL_ONTOLOGY.md`：object/link/action/function 驱动的开放 operational ontology 规范。
- `docs/15_COMPETITIVE_BENCHMARK.md`：相邻项目、机构背景、产品差异和公平比较方案。
- `prompts/`：总指令、8 个工作包 prompt、恢复/诊断/审查/验证 prompt。
- `sources/registry.json`、`sources/SOURCES.md`：已核验来源与未核验数据，禁止重新发明出处。
- `cases/`：真实道路证据候选、真实地点火灾候选和合成最小反例；不是伪造的真实数据。
- `verification/`、`tests/`：本包自带的可运行独立 oracle、Qwen System-One 协议验证、发布闸门测试。
- `evidence/PACK_TEST_REPORT.md`：本次实际执行结果；与未来产品测试分开。
- `MASTER_PLAN.md`：合并阅读版，不建议每次把全部内容注入模型上下文。

## 本包参考测试（现在就可执行）

```bash
python -m pip install -r requirements-verification.txt
python -m pytest -q tests
python scripts/audit_pack.py
python scripts/check_release.py evidence/product_release.json
```

最后一条在当前状态**必须失败**：产品尚未实现，不能冒充 v1 完成。该脚本是状态+证据文件完整性门卫，不是代替人工/CI审查的真实性证明。

`make test-unit` 等产品命令是 WP0 必须创建的接口，不是声称本包已实现这些产品命令。参考测试使用 `python -m pytest tests`，与未来产品 `test_suite/` 分离。


<!-- SOURCE FILE: AGENTS.md -->

# UrbanImpact Road & Fire — repository rules

## Mission and hard boundary
Deliver GIS v1 as an embeddable WEB plugin and a data-local analysis core. Real road restrictions + fire-induced EXTERNAL network impacts. Include typed temporal KG, deterministic PageRank/PPR, real local Qwen System-One integration, routing, a working SUMO adapter, tests, ablations, an evidence-labelled Helsinki example. Do not replace this with a QGIS plugin, 3D viewer, SaaS, CFD fire model, or mock demo.

## Read-once execution
Start with README.md, docs/00_PRODUCT.md, docs/10_EXECUTION.md and execution/work_packages.json. Thereafter load only the active work package's required files. Treat MASTER_PLAN.md as a reference, not recurring context. Follow prompts/00_MASTER.md; record the current checkpoint in execution/STATE.md.

## Engineering truth
- A tool exit code, test log, produced artifact hash, and declared scope establish completion, not prose.
- The supplied verification/ and tests/ are independent reference checks, NOT the product. Build the product under core/, api/, web/, adapters/, test_suite/.
- Mock Qwen System-One != real local Qwen System-One. Missing local model/runtime/GPU => BLOCKED_ENVIRONMENT, never PASS. Continue unblocked work. No fake fallback may satisfy the Qwen gate.
- The reference backend is pinned Reflex + Qwen3.5-4B, served locally. No closed Jev provider account/key is required. Pin exact Reflex commit, Qwen revision, device/dtype/permutations and calibration hash for release.
- Runtime city data stays in the deployer environment. Initial model-weight download may use Hugging Face, but production can use a pre-fetched local cache/mirror.
- Use the pinned Reflex/Qwen System-One contract in docs/05_QWEN_SYSTEM_ONE.md. Do not invent free-text outputs; Choice/Score/Noul stay typed and schema-validated.
- OSM/GTFS current snapshots are NOT historical truth. Incident location + assumed cordon is NOT actual fire perimeter. Announcement replay is NOT measured traffic validation.
- PPR is attention/relevance, not risk, causality, evacuation safety, or response-time prediction. Preserve physical metrics independently. Do not rank public policy choices or automate public resource-allocation decisions.
- Keep baseline/event node universe, seeds, alpha, relation policy and normalization equal for a claimed delta-PPR. Log separate policy-change experiments.
- Qwen System-One may adjust soft semantic relevance only, never road permissions, fire perimeters, speed, OD demand, capacity, travel time or safety rules.
- The operational ontology is normative: Objects + Links + Interfaces + Actions + Functions + Evidence. Users/LLMs must not directly mutate authoritative city objects or graph edges. Scenario changes go through typed Actions and immutable overlays.
- Authoritative city snapshots are immutable; Actions modify scenario workspace only. Every committed Action emits an ActionRecord and must be replayable to the same scenario hash.
- The PPR graph is a ProjectionSpec over the ontology, not the ontology itself. Audit/evidence/run objects do not enter ranking unless explicitly allowlisted.
- Palantir is an architectural inspiration only. Do not copy proprietary code/API or add a Foundry dependency.

## Scope and safety
No mandatory external AI. No author-operated backend. Municipal multi-user infra, auth/SSO, backups, HA are deployer-owned. Still implement safe local API binding/token, strict input paths, no arbitrary command execution, bounded jobs, credential redaction, explicit egress permission.
Fire UI is planning/research support, not operational dispatch or a substitute for emergency services. Unknown hazard boundaries must be user-confirmed/imported; never infer a certified radius from a severity adjective.
Keep future plugin seams small; no generic plugin marketplace/framework in v1. Cheap LLM is an optional provider interface only and cannot block v1 or overwrite numbers.

## Work cadence / anti-token-waste
Work in WP0–WP7 large end-to-end batches; each batch implements + tests + produces a demonstrable artifact. At most 3 hypothesis-changing repair iterations per failure signature. Two external access failures => record and route around, not repeated search. Do not repeatedly replan. Do not ask the user to re-confirm established scope.
Parallel agents only for disjoint file ownership and bounded deliverables; one integrator controls shared contracts/lockfiles. If no agent tools exist, execute serially; never simulate collaboration.
Do not contact third parties, publish/push/release, enable paid API, install unreviewed remote scripts or change system security without user permission. Providing a key alone does not grant unlimited budget.

## Verification / review
Preserve independent oracles and original failing tests. Never lower thresholds/remove assertions to pass. Changes to acceptance thresholds require a documented rationale unrelated to obtaining a positive ablation result.
Ablation variants share data, demand, seeds and physical outputs. No forced claim that Qwen System-One outperforms fixed PPR. If it does not, keep the verified integration and report the negative result.
Run focused tests after a change, full gates at work-package boundaries. Report passed/failed/skipped/blocked separately. A skipped release-required test blocks release.


<!-- SOURCE FILE: docs/00_PRODUCT.md -->

# 00 · 产品边界与最终可交付物

## 不是研究选题，而是一个完整工程产品

交付一个 Road & Fire GIS Web 插件。用户在宿主地图选道路、绘制限制区、指定事件时间和交通类别，运行情景，看到可追溯的道路/公交/设施影响及关系解释。首个宿主是自带的 MapLibre 参考 Web App；第二个宿主是无地图的 vanilla-HTML 控件集成测试，用来证明不是只能运行在自己大屏里的单体应用。

不要求第一版与所有 EU 数字孪生平台直接安装兼容。没有统一的“欧洲城市插件商店协议”。输出稳定的 Web Component、MapAdapter、HTTP API，将具体平台 SDK 集成留给后续适配器。

## 用户一次完整操作必须包括

打开本地部署 → 导入/选择已登记 citypack → 浏览数据日期/范围/缺失 → 选择道路限制或火灾事件 → 指定受限对象/时间/车种并确认假设 → 验证情景 → 运行 → 显示进度与取消 → 展示 baseline/event → 切换 A0/A2/A3 分析模式 → 选一个设施查看路由/图路径/来源 → 导出可复现结果包。

火灾场景不得因为没有三维楼体而失效；可以使用事件点/建筑轮廓。但没有楼层数据不得声称分析三楼与四楼的传播差异。无警戒区信息时，不自动产生所谓正确警戒半径；让用户明确输入“情景假设”。

## v1 必须有的五组结果

1. **道路与路由事实**：车种/方向/时段受限，绕行距离和固定权重网络行程时间差，不可达/未完成单独统计。
2. **SUMO 情景结果**：相同 demand、seed 下 before/after 行程时间、未到达数、队列/路段速度（有输出才展示）。默认 synthetic demand 必须有醒目标记。
3. **公交与设施关联**：公交路线潜在受影响、设施接入变化；没有可靠公交道路匹配只能显示 candidate，不是取消或延误实测。
4. **图注意力**：typed KG、固定 PPR、Qwen-System-One-PPR、条件相同的 delta-PPR；不把小数标为风险百分比。
5. **证据与重放**：数据版本、假设、模型版本、Qwen System-One provenance、关系来源、图大小/截断、指标单位、缺失信息、消融报告。

## 完成 != 所有城市预测都准

`engineering_complete` 要求所有必须功能和真实集成跑通。
`source_replay_verified` 只覆盖已核验公告/人工映射事实。
`measured_prediction_validated` 需要独立、同一时期的真实观测；缺失就为 NOT_VALIDATED。

可以发布明确标注边界的 GIS v1，但不得将没有测量证据的产品宣传为实战交通/火灾预测器。不能用“调通 API”替代“模型判断有增益”，也不能因为没有增益就伪造漂亮消融结果。

## 本版不做

账户/组织管理、SaaS、中心数据托管、多人编辑冲突、城市内网部署代运维；3D Tiles/CityGML/BIM 核心依赖；FDS/CFAST/火焰和烟羽预测；实际消防派车、真实应急路线推荐、安全撤离指令；装修/洪水/全套活动插件；训练 GNN 或新基础模型；多城市大规模同步；实时 HFP 永久在线订阅；通用自然语言自主操作平台。

## release acceptance

全部必须闸门参见 docs/11_RELEASE.md；缺少真实 Qwen System-One 或真实 citypack 测试就不能称“第一版全部正常运作”。提供缺口状态，不通过编造或 mock 消除缺口。


## v1 的产品差异：Operational Ontology

Road/Fire 并非直接 patch GIS 图层：道路、设施、事件、restriction、scenario、run、evidence 与 impact observation 使用 versioned typed objects/links；用户操作通过 typed Actions 写入 scenario overlay，authoritative city snapshot immutable。Web Object View围绕对象展示事实、links、attention、证据和允许的actions。详见 docs/14_OPERATIONAL_ONTOLOGY.md。


<!-- SOURCE FILE: docs/01_ARCHITECTURE.md -->

# 01 · 架构与实现取舍

## 固定结构

```text
Host web app + <urban-impact-panel> + MapAdapter
                      │ same-origin / deployment-owned endpoint
                   FastAPI
                      │ local jobs + filesystem / SQLite metadata
            ScenarioService / RunManifest
          ┌───────────┴─────────────────┐
          │                             │
     Routing graph                 Scenario KG
  direction / turns / time       IDs / types / provenance
          │                             │
  deterministic router + SUMO   SciPy CSR PPR ← Rules / Qwen System-One
          │                             │
          └──────── facts + attention ──┘
                        │
                 ResultBundle / exports
```

有两个图：**可通行路网**决定能否走和代价；**语义依赖图**决定哪些事实有关联。不要将它们混成一张 unit-weight graph。几何在 GeoParquet/GeoPackage，图用实体 ID 和索引关联。

## 选定工具，而非给 Codex 无尽选型

- Python 3.12 作为首个参考运行时；FastAPI/Pydantic，NumPy/SciPy CSR，NetworkX 仅用小图 oracle；Shapely/PyProj，PyArrow/GeoParquet，SQLite 作本地 job metadata。
- OSM 导入使用成熟解析器和 SUMO netconvert；不要自己重写 XML/PBF 解析和交通信号模型。生产 routing 必须保留方向、转弯、权限。可直接从 SUMO edge/connection 建立 edge-state routing 图，与独立小图 oracle 对照。
- GTFS 读取常规 CSV；规范日期、calendar_exceptions、>24:00。首版仅 verified road-aligned bus route dependencies，轨道交通交叉不得硬套道路封闭。
- SUMO 以子进程/TraCI adapter 运行，与 Python 包分开版本锁定。参考容器含确定版本 binary；不要 shell=True。
- TypeScript + Lit Web Component，MapLibre GL JS reference adapter，Vite 构建，Vitest + Playwright。
- pytest / Hypothesis（开发时增加）/ Ruff / 类型检查；CI 按 fast、SUMO、browser、data、local-system-one、release 分层。
- 不引入 Neo4j、Kafka、Kubernetes、Redis、vector DB、GPU。SQLite worker 一次一个重任务足以参考部署；组织可用外部 executor。

以上为项目设计，不声称这些依赖已经在本包全部安装。WP0 检查官方兼容性并生成锁文件；版本变动不能静默升级。生产依赖许可逐项登记，项目代码建议 Apache-2.0，数据库和数据包许可独立，不能把 OSM 数据自动变成 Apache 数据。[S04,S11]

## 目标仓库

```text
core/urbanimpact/{contracts,citypack,network,graph,ranking,scenario,results}/
adapters/{sumo,osm,gtfs,system_one,llm_optional}/
api/                       # same-origin local reference API
web/{plugin,maplibre,reference-host,headless-host}/
test_suite/{unit,property,integration,sumo,browser,data,live,outcomes}/
experiments/{variants,labels,splits,reports}/
deploy/{Dockerfile,compose.yaml,env.example}/
data/{raw,normalized,manifests}/       # raw files gitignored
runs/<run_id>/                       # immutable run artifacts
```

原 handoff 文档留在 docs/、prompts/、sources/，参考 oracle 留在 verification/、tests/，防止与生产测试混淆。

## 主要接口（先锁类型，再并行）

```python
CityPack.load(manifest) -> VerifiedCityPack
Scenario.validate(citypack) -> ValidationReport
RestrictionCompiler.compile(scenario, snapshot) -> RestrictionSet
Router.compare(pair_spec) -> RoutingFactBundle
SimulationAdapter.run(pair_spec, cancel_token) -> SimulationFactBundle
GraphProjector.project(citypack, facts, scenario) -> PairedGraphProjection
RelationPolicy.score(context, allowed_relations) -> PolicyRecord
Ranker.compare(projection, frozen_policy, seed_spec) -> RankComparison
Explainer.paths(rank_result, projection) -> EvidencePathBundle
Exporter.write(run_manifest, bundles) -> ResultBundle
```

协议清楚，不要求搞抽象工厂森林。每个接口 v1 只有一套主实现和必要对照。数据契约由 integrator 拥有，其余代理不得擅改。

## 缓存与差分

内容寻址 cache key 包含输入 sha256、代码 commit、城市快照、ROI、scenario、时刻、车种、归一化方法、Qwen model/revision + Reflex commit + calibration hash、rubric hash。physical facts 只由物理输入决定，切换 A2/A3 不重跑 SUMO。UI 结果和计算缓存不能共用无 scope key。Qwen System-One unavailable 运行必须标记 RulesFallback/BLOCKED_ENVIRONMENT，禁止伪装 Qwen System-One。

## 扩展边界

future plugins 仅通过 `Restriction`, `DemandOverride`, `IncidentMetadata` 等少量契约接入。Noise/dust/flood primitives 不在 v1 实现；保留 schema version 和 adapter protocol 已足够，不预造通用工作流平台。


## Operational Ontology semantic layer

GIS v1 增加 `ontology/` 语义层，详见 `docs/14_OPERATIONAL_ONTOLOGY.md`。它不是新数据库，而是所有 API/UI/graph projection 的类型契约。

```text
City snapshot (immutable)
        │
Operational Ontology objects/links
        │
Typed Actions → Scenario Overlay → Action Log
        │                         │
        ├── deterministic Functions
        ├── SUMO Functions
        └── ProjectionSpec → Scenario Graph → PPR
```

目标仓库新增：

```text
ontology/{manifest.yaml,registry.py,codegen.py}/
core/urbanimpact/actions/
core/urbanimpact/ontology/
web/plugin/object-view/
comparison/{feature_matrix.csv,reproduction_notes/}/
```

Web/LLM 只能提出或提交 Action；不得存在公开的任意 `edit_relation` / `set_road_closed` 数据库写接口。Road closure 是 `RoadRestriction` object + Scenario overlay。


<!-- SOURCE FILE: docs/02_DATA_CASES.md -->

# 02 · 首城 Helsinki：公开事件、公开数据与证据边界

研究核验日期：2026-09-23。选择 Helsinki 是因为找到**具体道路活动公告 + HSL 官方公交/OSM 开放数据入口 + 同城真实火灾报道**，不是因为证明它比其他城市更好。

## Road Case R1：Helsinki City Run 2026-05-15–16

市政府于 2026-05-11 发布公告，列出南向 Mannerheimintie（Opera 至 Pohjoinen rautatiekatu）、Helsinginkatu（Mannerheimintie 至 Sturenkatu）、Mäntymäentie 等受限道路；另列 Baana 步行/骑行的时间。[S01]

**只复述已给出的限制；不能把 Baana 的小时范围赋给所有机动车道路。** 公告说明“计划中的限制”，不是实际实施 GPS 记录。Mäntymäentie 日期范围不能自动提升为精确起止小时。

文件 `cases/helsinki_cityrun_2026/case_evidence.json` 已预置事实候选，未编造 OSM way IDs、坐标、车种豁免或完整真实限行时间。

R1 在 WP1 必须转为可运行案例：下载路网→定位公告端点→选择有向 road segments→生成 review map→核对人工映射→保存每个匹配证据/不确定字段→必要时以一个明确“假设这些已公告限制同时有效”的 snapshot 运行。时间不完整时该 snapshot 是 what-if，不叫历史逐分钟 replay。

## Fire Case F1：Kalasatama / Leonkatu 公寓火灾

Yle 依据其取得的事故说明报道，事件位于 Leonkatu 公寓楼，通知时间为当地 20:55；报道涉及四层阳台。[S02] 当前方案只使用地点、通知时间等事件事实；不使用居民身份、不分析责任和原因，也不复制新闻全文。

**现有证据不包含可直接验证的完整封路几何、实际警戒区、消防车 GPS 和独立交通延误。** 另篇原始报道的图片说明明确写明火灾发生于2026-05-23，已核实日历日期。[S21] 门牌/坐标仍需核实；不得只凭街名捏造建筑中心点。

F1 分两部分：
- `incident_facts`：新闻/官方来源确认的真实事件事实。
- `scenario_assumptions`：用户画出的道路限制/警戒区及有效时段；明确标成 assumed，不自动生成安全半径。

因此 F1 初始验收名称是 **“真实地点火灾情景分析”**，不是“历史火灾交通预测已验证”。若后续取得真实管制/公交公告，再升级对应字段证据，不升级不存在的其他证据。

## 公共数据

### OSM 路网/设施

官方 HSL 数据页提供 OSM 区域提取入口；读取该目录获取实际文件名，再 pin 下载 URL+sha256。[S03] 主数据可包含道路、医院、消防站、公共交通站点；OSM 数据遗漏与 outdated tags 要明确报告。

历史事件优先使用截至事件前的快照。有可合法获取的历史快照则 pin；否则 current snapshot 只能用于 **current-network reconstruction / stress test**，不可写为2026年5月历史实况。不得利用事后更新的医院/路网静默增加准确度。

不要为了裁切小区域提前破坏长距离绕行。为整个候选情景留外圈路网；实际裁切半径通过扩大边界稳定性测试决定。

### HSL GTFS

官方最新 ZIP：https://infopalvelut.storage.hsldev.com/gtfs/hsl.zip 。官方说明每日更新并面向未来约两个月，因此当前下载不是历史时刻表。[S03]

每次记录 feed_start/end 或从 calendar 验证覆盖。历史 feed 找不到时，R1 的历史公交状态必须 NOT_VALIDATED；可另外展示当前 feed 下的反事实影响，不混在历史预测分数里。

HSL 页面说明其数据多数 CC BY 4.0，而 OSM 衍生数据有 ODbL，必须按实际源做 attribution。[S03] 不把可下载等同于可随意镜像。

### HFP/GTFS-RT/真实计数

实时接口存在不等于有公开历史归档。HSLdevcom/hfp-analytics 的 README 自述 API 当时非公开，不能将该 repo 当成可下载历史 GPS 数据。[S07]

HRI 有 Helsinki 交通量数据目录 [S08]；本次仅找到目录，没有核验该事件日期与路段的可用文件。WP1 最多两轮源核查：拿到真实文件，检查 timestamp、计数器坐标、车流/速度单位、许可、事件前后覆盖，再决定能否用于 outcome validation。没有就明确停止，不反复抓取或虚构。

## 数据落地流程

1. `fetch --source <registry_id>` 下载到临时文件；HTTP类型/长度/超时/总量限制；SHA256；原始字节不改写。
2. `inspect` 生成源日期、extent、CRS、行数、对象类型、许可、异常和未知；未知不自动修复成默认值。
3. `normalize` 产生版本化实体ID、geometry refs、edge IDs、road↔SUMO mappings、GTFS coverage。
4. `verify` 产生人工可查的端点/有向路段地图与 CSV，记录 reviewed_by、review_method。代理自检不得冒充独立人类专家。
5. `freeze` 冻结 citypack 和评估 labels；模型只读取 inference allowlist，不读取 heldout outcomes。

当前容器直接下载外部数据因网络/DNS限制失败；本包**没有附带完整 Helsinki PBF/GTFS**。官方网页核查已完成，但 `bytes_downloaded=false`。WP1 的文件级验证必须在开发环境真正执行。

## 数据规模目标（项目预算，不是测量结论）

目标 reference pack：先以覆盖事件及替代路径的城区/城市路网验证，不承诺“全城都被准确模拟”。路网10万有向边、semantic graph约20万边作为第一组性能测试；扩大只在边界/性能报告支持时做。内存、耗时以实测填写，不给未经跑分的秒级承诺。

## 结果验证三层

- V1 源事实/拓扑：公告道路匹配、车向、时段精度、设施 snap、限制编译正确。
- V2 独立运行变化：独立公交管制通告、道路开放/关闭记录；推理输入中不可提前包含作为 heldout target 的最终受影响路线名单。
- V3 数值预测：事件时段传感器/公交实测延误，加前后基线和对照日/控制区域；无数据不评分。

R1/F1 真实案例各写一张 data/evidence card；不得一律叫“real world validated”。


<!-- SOURCE FILE: docs/03_CONTRACTS.md -->

# 03 · 契约：所有结果都能知道“依据什么”

JSON Schema 的初稿在 contracts/。它们是 wire-level 最低约束，生产 Pydantic 仍需做跨字段校验。必须从同一权威模型生成/一致性测试 TS types 与 OpenAPI，不能维护三个逐渐分叉的定义。

## Scenario v1

`schema_version, scenario_id, citypack_id, kind(road|fire), timezone, analysis_at, window, restrictions[], incident?, assumptions[], objective, engine, ranking, seed_spec`

restriction 必须有唯一 ID、**有向 edge IDs**、valid_from/to、blocked vehicle classes、evidence_ref、evidence_kind(observed|announced|assumed)。未知小时不可假装 observed；用 bounded uncertainty 字段和明确分析时刻假设。before/after window 为 UTC ISO8601，UI 用 Europe/Helsinki 显示。

fire.incident 的位置可为点或 geometry_ref；`fire_floor` 缺失允许，但设置 floor 不自动开启楼层传播。`perimeter_source=user|imported`，无默认火灾“等级→半径”映射。

## KG contracts

entity: `id, type, source_id, external_id, geometry_ref?, valid_from?, valid_to?, attributes`。
relation: `id, src, dst, relation_type, evidence_refs[], asserted_or_derived, derivation_id?, valid_from/to, confidence_status, base_strength`。

实体/关系 schema 必须列出合法 source/target 类型与传播方向。每个派生 `ROUTE_USES_SEGMENT` 或 `FACILITY_ACCESSED_VIA` 都保存路线/匹配的依据；仅 NEAR 不得被强制当成 SERVED_BY。

## Result fields：事实和注意力分开

每项 numeric metric 都带 `value, unit, definition_id, scope, evidence_level, uncertainty, numerator?, denominator?`。不可达用 `status=unreachable,value=null`；不要用 Infinity 进入 JSON，也不要默认为0。

rank record 含 `attention_score, delta_attention, rank_within_type, policy_hash, seed_hash, node_universe_hash, alpha, residual_l1, convergence, explanation_paths`。不提供 `risk_percent` 字段。

System-One policy record 使用 `policy.schema.json` v1.1，除 scores 外必须保存 backend/model revision、permutations、calibration hash（可空但必须显式）、device/dtype 与 applied transition hash；token usage 只是可选诊断字段，不再是本地 Qwen 完成条件。

`ResultBundle` 必须标明 `demand_kind=synthetic|estimated|measured`、`network_temporality`、`transit_temporality`、`simulation_status`、`provider_mode=local_qwen|replay|rules|mock_test`。前端不能去掉这些标签。

## 本地 API（WP0 创建并保持稳定）

- `GET /v1/health`：版本和依赖能力；不泄露API key是否具体是什么。
- `GET /v1/capabilities`：数据/引擎/Qwen System-One模式，缺失功能原因。
- `POST /v1/citypacks/import`：仅上传/已授权本地路径，不是任意远程URL下载代理。
- `POST /v1/scenarios/validate`：语法、空间、时间、数据覆盖、事实/假设报告。
- `POST /v1/runs`：创建 job，202、run_id、status_url；幂等键绑定规范化输入。
- `GET /v1/runs/{id}`：queued/running/completed/failed/cancelled，stage进度，不能虚报0–100。
- `POST /v1/runs/{id}/cancel`：终止子进程树，原子标记，不删除别人的文件。
- `GET /v1/runs/{id}/results`：JSON摘要+本地artifact引用。
- `GET /v1/runs/{id}/export`：ZIP，来源、assumptions、metrics、graph、rank、manifest。

轮询足够；不强制 websocket、消息队列。错误结构统一 `code,message,stage,retryable,details_redacted`。reference服务只认部署方local token，同源proxy；多人身份在边界外。

## 外部调用边界

下载源只由本机配置登记；模型只接受脱敏relation描述和objective。任何申请权限、改变限行、改变baseline的数据变更必须 deterministic 校验+用户确认。LLM解释不能改ResultBundle。


## Operational Ontology contracts

`contracts/ontology_manifest.schema.json` 与 `contracts/action_record.schema.json` 是新的最低 wire-level 契约；完整语义在 `docs/14_OPERATIONAL_ONTOLOGY.md`。生产实现必须从单一 ontology manifest 生成或一致性校验 Pydantic/TS/JSON Schema。

- authoritative object 不可被 scenario Action 覆写；
- restriction/fire incident 是 scenario objects，不是 RoadSegment 的裸字段 patch；
- Action 先验证 preconditions，再原子提交 overlay；失败不允许 partial commit；
- LLM 只能返回 Action draft；同一 validator 负责用户/UI/LLM 来源；
- ResultBundle 新增 `ontology_version, scenario_overlay_hash, action_log_hash, projection_id, projection_hash`；
- export ZIP 必须包含 ontology manifest version 与 ActionRecords。

本地 API 在实现时增加：
- `GET /v1/ontology`：类型/能力摘要，不返回城市数据；
- `POST /v1/actions/validate`：typed Action preflight；
- `POST /v1/actions`：提交 scenario Action；
- `GET /v1/scenarios/{id}/actions`：场景操作日志；
- `GET /v1/objects/{id}`：Object View 所需 identity/state/links/facts/evidence/actions 摘要。


<!-- SOURCE FILE: docs/04_KG_PPR.md -->

# 04 · 知识图谱与 PageRank：真正参与运算、可独立验证

## 不能装饰性“接上知识图谱”

v1 关系类型：ROAD_CONNECTION（从合法路网导出）、ROUTE_USES_SEGMENT、FACILITY_ACCESSED_VIA、STOP_ON_ROUTE、CELL_ACCESSES_FACILITY（有OD结果才建）、INCIDENT_RESTRICTS（事件元数据，可从PPR projection排除）、NEAR（仅候选关联）。

原始 source 事实与派生事实分开；关系的逆方向若需传播，显式建反向 relation，不能把所有边变无向。比如从受限道路寻找使用它的公交线，PPR投影要使用 `SEGMENT_USED_BY_ROUTE`，不能把逻辑方向写反。

图只保存ID、relation type、有效时间、来源与权重；geometry不进入每次Qwen System-One请求。projection保留 source IDs，可随时回到GIS图层检查。

## PPR 数学约定

固定 `alpha=0.85` 表示**继续沿边走**的概率，restart是1-alpha，与NetworkX API约定一致。[S10]

\[
r=(1-\alpha)s+\alpha P^T r,\quad \sum_i s_i=1,\quad P\mathbf1=\mathbf1.
\]

稀疏CSR power iteration为主；dense linear solve仅用于小图独立oracle。负值/NaN/inf直接拒绝。dangling row分配到s。要求数值测试 `mass_error<1e-10`、`residual_l1<1e-10`（小图），大图默认 `residual_l1<=1e-8`，保存实际值和迭代次数；不收敛不是PASS。

## relation-aware transition，不靠连接数量偷分

对节点i的一种关系t，先做关系内部归一化，再做关系之间混合：

\[
Q_{ij|t}=a_{ijt}/\sum_{k\in N_t(i)}a_{ikt},\quad
\pi_i(t)=m_t g_t/\sum_{u\in T_i}m_u g_u,\quad
P_{ij}=\sum_t\pi_i(t)Q_{ij|t}.
\]

`a` 是已定义的非负关系强度；未评估confidence仅做数据标签，不默认将数据贫乏区域的重要性乘为0。`m_t`为显式baseline profile，`g_t=epsilon+(1-epsilon)*score_t`，epsilon默认0.10作为待敏感性验证的工程参数，非科学常数。专家/规则硬排除的关系不让Qwen System-One重启。

同一出边只有一种relation type时，统一乘Qwen System-One分数会被行归一化抵消——**这是数学事实，不是接入失败**。必须提供含多种relation的fixture证明Qwen System-One能改变transition；也测试单一关系场景不变。不为了制造排名变化偷偷加随机扰动。

## before / after 可比性（最重要）

构建pair时取两张图的统一实体集合U，排序稳定，事件本身若只是元数据则两边均排除。相同 `s, alpha, m_t, g_t, normalization`、同一snapshot。被封闭道路仍可作为semantic asset存在；在routing graph禁止走，不意味着从KG删除被影响对象。

first use：将用户选择的road IDs映射成统一seed，baseline和event用同一s。需要按实际延误改seed的额外分析叫 `event_evidence_attention`，不能与原baseline直接叫纯delta。

\[
\Delta r=r_{event}-r_{baseline}.
\]

改变Qwen System-One objective/profile是独立policy ablation，不能混入closure effect。总和Delta为0；局部分数下降可能是其他位置得到更多概率质量，不能解释成该处风险下降。

## 为什么不直接把PPR叫影响

真正的延误/可达性由router/SUMO产出。PPR只用于在已有facts和关系里排序检索/浏览。先显示事实指标，再显示“关联关注度”。候选检索可以topK，但**不得用Qwen System-One/PPR裁掉固定必查的医院/消防设施**；硬规则检查和图排名分离。

## 解释

每条解释必须引用实际graph edge IDs和source refs。可输出2–3条贡献较大的有界walk或dependency witness，并注明“该路径支持关联解释，不证明物理因果”。

PPR完整概率来自所有walk；一条最短路径不是全部分数来源。选择做精确walk贡献时使用 `(1-alpha)*alpha^k*path_transition_product*seed_mass`，显示覆盖质量与截断上界；否则仅称witness path，不能捏造contribution%。

## 计算规模

完整路由边界与scenario semantic projection不同。优化先缓存/CSR/局部projection，不先写增量PPR。用扩大外圈检验critical metrics稳定；若不稳扩大或标记 boundary_truncated。人口网格到每个设施的全连接会爆炸，按明确OD/coverage需求建立有限关系，保留未分析范围。

## 必须消融

A0 GIS/router/SUMO；A1+typed reachability；A2+fixedPPR；A3+QwenSystemOnePPR；A4Qwen System-One-noPPR；A5permuted/neutral weights。具体公平比较在docs/09_VALIDATION_ABLATION.md。


## operational graph 与 dependency graph 的具体更新规则

事实层保留两列 `baseline` / `scenario`，不是覆写原始路网。对于有 verified 路径的设施/公交，分别从该时刻合法路径产生 operational dependency edges；改变后的路径可改变边集合/strength，统一实体集合U后计算paired PPR。每项变化写入 `graph_delta_log`，含原关系、变更后关系和对应router/SUMO fact IDs。

静态的“某公交历史上用此路段”仍可留在dependency evidence层，以便解释为何它可能受扰动；不能把它误当已经绕行后的实际路线。两个projection必须有不同`projection_kind`，禁止把它们无说明混合成一个分数。

若手头只有静态关系，缺少足以更新operational graph的资料，使用 `event-seeded attention` 即可；baseline/event图实际相同则delta=0，报告“无法由这些数据识别结构变化”。不凭空修改边权来制造影响。对用户最重要的可达性事实仍由router独立产出，不依赖PPR是否变化。

baseline指**同一分析时刻、同一外部条件但没有本次restriction**的反事实，不是昨天和今天随便两张图。Qwen System-Onepolicy变化实验只叫policy ablation，不叫事件delta。本包reference_outcomes演示的正是policy ablation，已用not_event_delta=true明确标记。


## Ontology projection boundary

从 handoff-3 起，typed KG 是 Operational Ontology 的**分析 projection**，不是全部 ontology。`Scenario`, `ActionRecord`, `EvidenceSource`, `SimulationRun` 等可存在于 ontology，但默认不进入 PPR。每次 ranking 保存 `ProjectionSpec`：允许 object/link 类型、时间、objective、policy 与 source snapshot hashes。

任何代码若直接遍历“全部 ontology links”生成 PPR 都必须被测试拒绝。Road/Fire Action 改变 scenario overlay，deterministic Functions 先产生 operational facts，再由 projection 构建 scenario graph。


<!-- SOURCE FILE: docs/05_QWEN_SYSTEM_ONE.md -->

# 05 · Qwen System-One：本地 Jev-style 决策层（Reflex 参考实现）

核查日期：2026-09-23。[S22–S24] 第一版不再依赖 closed Jev provider/Jev 注册、密钥、付费 API 或供应商可用性。UrbanImpact 自己定义 `QwenSystemOneBackend` 契约；第一版参考运行时采用 **Reflex + Qwen3.5-4B**，在部署者环境内本地推理。Reflex 是参考实现，不应成为核心算法的不可替换依赖。

## 为什么选这个实现

参考实现 `kshetrajna12/reflex` 是 MIT 许可的开源 Jev/System-One 重建，默认使用 `Qwen/Qwen3.5-4B`；Qwen3.5-4B 权重为 Apache-2.0。[S22][S23] Reflex 提供 `POST /v1/systemone`，输入 state + typed questions，输出 `noul / choice / score` 概率分布，不生成自由文本；README 明确说明可将原 Jev 客户端改 base URL 指向本地服务。[S22]

不要把另一个 `pngwn/system-one-qwen3.5-4b-scorer` 作为默认发布依赖：它很适合研究对照，但模型卡当前是 CC-BY-NC-4.0，且作者明确列出若干高基数/长上下文限制。[S24] 可以在研究消融中单独比较，不能无意把非商业限制带进主发行版。

## 参考运行形态

开发/发布参考服务器：

```bash
git clone https://github.com/kshetrajna12/reflex
cd reflex
git checkout <PINNED_COMMIT_OR_TAG>
uv sync
uv run reflex-serve --stable --port 8008
```

UrbanImpact 只调用：

```text
http://127.0.0.1:8008/v1/systemone
```

`stable` 是移动配置，**发布必须解析并记录精确 Reflex commit、Qwen model revision、precision/device、permutations 和 calibration file hash**，不能只记录 `stable`。首次下载 Qwen 权重需要网络；机构离线部署应预取/镜像权重，运行期不要求数据出网。

Reflex 当前文档对其发布用 4B 路径给出的参考是 **16 GB CUDA GPU**，并提供较小 0.8B WebGPU 演示；该演示明确不是发布质量替代品。[S22] 因此 UrbanImpact 的 release gate 以经过 UrbanRelationEval 的 Qwen System-One 实例为准，而不是以“能启动某个小模型”为准。若开发机没有合适 GPU，可把同一 `/v1/systemone` 服务部署在部署机构自己的 GPU 主机上；只要 endpoint 留在部署方环境、经过明确配置并记录 egress scope，仍符合 data-local 边界。


## 后端抽象与替换规则

核心代码只依赖 UrbanImpact 的 typed decision contract：`state + questions -> Choice/Score/Noul probabilities`。`ReflexBackend` 是 v1 的参考实现；不得把 Reflex 的内部 Python API 散落到 graph/ranking 代码。所有调用统一经过 `QwenSystemOneBackend.score_relations()`，这样未来可以替换为另一个 Qwen System-One 实现而不重写 KG/PPR。

发布默认 profile：

```text
backend_contract = qwen_system_one_v1
reference_server = reflex
model            = Qwen/Qwen3.5-4B
transport        = local/private HTTP /v1/systemone
free_text_output = forbidden
```

`pngwn/system-one-qwen3.5-4b-scorer` 可作为研究消融，但当前许可为 CC-BY-NC-4.0，不作为默认发行依赖。[S24]

## UrbanImpact 请求约束

本版继续使用 `Score` 给 relation type 的**任务相关性**评分，不让多个都相关的关系在一个 Choice 中被迫互斥。

```json
{
  "state": {
    "task": "urban_dependency_retrieval",
    "objective": "facility_access",
    "privacy": "abstract relation types only"
  },
  "questions": {
    "SEGMENT_USED_BY_ROUTE": {
      "type": "score",
      "instructions": "Assess semantic relevance of relation SEGMENT_USED_BY_ROUTE: a transit route uses this road segment. Do not infer delay or physical risk.",
      "criteria": ["Not relevant", "Indirectly relevant", "Directly relevant"]
    }
  }
}
```

UrbanImpact adapter 不依赖自由文本；逐问题验证 type、finite score、概率和≈1、score 与概率加权等级一致、legend 完整。服务端若返回额外 model/usage 字段可作为 provenance 保存，但 release 不能依赖供应商 token/billing 字段存在。

## 真正的数据流

`local Qwen System-One → checked scores → policy record → typed relation mixing → PPR → ranked entities → report provenance`

完成条件不是“本地服务返回 JSON”。必须：

1. 在多 relation fixture 上证明真实 Qwen 响应改变 transition matrix，且实际进入 PPR；
2. 在单 relation row 上验证统一缩放会被归一化抵消，不能伪造增益；
3. 在 Helsinki scenario graph 上消费真实本地响应并保存 transition hash；
4. 保存 pinned model/config/calibration provenance，而不是保存整张原始 KG；
5. A3 不必胜过 A2；如果没有增益，报告负结果，固定 PPR 仍可作为产品默认。

## 校准：必须按 UrbanImpact 自己的数据做

Reflex 自己强调温度校准应该针对部署工作负载拟合，模型/prompt/precision 变化后需要重做；它的通用 benchmark 不能替代城市域校准。[S22]

因此 WP6 增加 `UrbanRelationEval`：

- `calibration` 与 `test` 按 scenario family / corridor 分组，禁止同母题泄漏；
- calibration split 只用于 temperature fitting / threshold 选择；
- test split 冻结后不做 prompt 调参；
- 报告 accuracy/NDCG（如适用）、Brier、ECE、option-order sensitivity、重复运行稳定性；
- 小样本不宣传“已校准”，只报告观测值与样本量；
- v1 默认**不** LoRA 微调。只有独立证据表明 frozen 4B 在城市 relation task 不够且有足够训练数据时，才作为后续实验，不用 test set 反向训练。

## 数据本地化与安全

本地 System-One 是第一版的优势：默认不把城市数据发给 closed Jev provider、OpenAI、DeepSeek 或其他供应商。Web 插件不能直接把城市数据送到模型服务；调用发生在部署者的 UrbanImpact Core 内部。

默认请求仍只包含：event category、objective、relation definition、匿名/聚合上下文；**不发送 geometry、整张 KG、个人数据**。这样即使未来把 endpoint 放在机构内网另一台 GPU 主机，也保持最小披露。

若 `base_url` 不是 localhost，adapter 默认拒绝，部署者必须显式 `allow_remote_endpoint=true`；报告中标记 `data_egress_scope=organization_network` 或 `external`，不把“自托管”与“本机”混为一谈。

## 性能与成本账本

System-One 不再有按 token 付费 gate。记录的是：

- model bytes / first-load time；
- wall latency；
- questions/request；
- forward passes / permutations；
- GPU/CPU device、dtype、peak RSS/VRAM（能可靠测时）；
- calibration hash 和 cache hit；
- 模型下载是否已离线镜像。

不对每条 graph edge 调模型。优先给 relation types / small candidate context 批量评分，再交给 PPR 扩散。相同 `{model revision, calibration hash, objective, rubric, relation schema}` 的结果内容寻址缓存复用。

## 廉价 LLM 仍是独立层

DeepSeek、GPT-5.6 Luna 或其他廉价语言模型仍通过 `LanguageBackend` 可选接入，用于 scenario 草稿解析、歧义解释与最终文字说明。它们不是 Qwen System-One 的替代品，也不能修改路权、速度、OD、火灾范围或物理指标。远程 LLM 继续 BYOK、默认关闭；其数据出网与费用由部署者明确配置。

## 随包 smoke

先单独启动本地 Reflex/Qwen 服务，再运行：

```bash
python scripts/qwen_systemone_smoke.py
```

默认只允许 loopback。如果服务没启动，返回 `BLOCKED_ENVIRONMENT`，不会把 mock 当成通过；如果成功，它只证明 typed protocol 正常，不能代替 WP3 的真实 graph integration gate。


<!-- SOURCE FILE: docs/06_ROAD_FIRE_SUMO.md -->

# 06 · 道路与火灾：建模边界和仿真实现

## Road v1

支持有向edge的时间窗全封闭、指定车种封闭、车道限制（有lane mapping才支持）；不完整lane数据返回unsupported，不能将降容偷偷改为全封。

基础路由输出是固定travel-time权重最短路差：`distance_m`, `travel_time_s`, `reachable`，不是实时拥堵预测。速度缺失时采用显式road-class假设profile，保存assumption，禁止LLM猜速度。桥梁/隧道平面相交不自动连通；设施入口与最近主干道路几何中心不同。

消防类车辆的权限、限高/宽、逆行、信号优先不从一个`emergency`标签自动推导。v1默认保守服从已知限制；由用户明示可通行的道路才能放行。消防站到事件的`network travel time`不是call handling+turnout+travel的总响应时间，也不代表该站有可用车组。

## Fire v1

火灾输入点/建筑轮廓、时间、人工/外部确认的限制区/道路。计算外部网络变化与potentially associated facilities。没有烟/热模型就不输出烟羽、死亡概率、传播时间、疏散安全性。事故点周边buffer只允许用于选择候选数据，不自动成为风险/封闭区。

用户明确录入的圈定区域用于道路限制候选，逐条确认方向和车种。禁止“中等火灾默认100m”这种伪消防标准。火灾假设不自动影响OD出行需求；需求变化只有显式参数且marked assumed才加入。

## SUMO paired runs

同一net文件、同一OD/demand文件、same random seeds、同一warmup和分析窗口。baseline与event只改变明确的restrictions（或单列demand变化因子）；不能每次randomTrips不同再比较。

显式记录network conversion options、signals assumptions、car-following配置、rerouting比例和knowledge假设。多scenario共用physical cache。

[S09]官方文档一个关键陷阱：`closingReroute` **不带allow/disallow是soft closure**，无替代路径的车可能继续走。hard closure必须使用权限并测试车辆日志。多rerouter配mode8有循环风险；统一同时段closures，禁止用全局ignore-route-errors掩盖输入错误。

默认对验证fixture禁用/严格记录teleport。生产report同时报告`arrived, unfinished, teleported, rejected_departures`，只平均成功到达车辆会偏差，不能把未到达算0分钟。设置最大simulation duration、max vehicles、wallclock timeout、output size、取消子进程树。

## 两类SUMO成果

- `SYNTHETIC_DEMAND_WHATIF`：可证明工具和情景机制工作，不能证明真实拥堵数值。v1必须至少提供这种真实SUMO运行。
- `CALIBRATED_MEASURED`：取得真实OD/计数，校准仅使用训练部分，再对独立事件/控制日验证。无数据不开放此badge。

## 必须的SUMO集成fixture

小型双通道网络：baseline皆可走，关闭短通道后车辆用长通道；唯一通道全封则未到达/等待；允许特定class仅该class可进入；closing起止边界；同时两处限制无循环；取消kill child；相同seed baseline重跑结果hash/数值一致；异常日志导致失败而不是地图绿色完成。

## 路网裁切

离事件近不代表受影响大，远端绕行可能关键。先路由边界A，再A+外圈，比较OD可达性、绕行时间、关键设施指标；变化超过预声明阈值扩大或标记未稳定。不能在建semantic graph前随意删掉医院所在外围区。


<!-- SOURCE FILE: docs/07_WEB_SECURITY.md -->

# 07 · Web 插件与本地数据原则

## 两个真实宿主验收

1. MapLibre reference host：道路、设施、闭合区、before/after、时间轴、影响表、解释面板。
2. 独立vanilla HTML host：加载同一个构建产物、连接同一API，创建/查看/导出情景；MockMapAdapter测试生命周期。不得复制一份面板代码假装嵌入。

`<urban-impact-panel>`使用Shadow DOM样式隔离、键盘可达焦点/label、dispose解除订阅。只导出必要事件`scenario-change,run-complete,entity-select,error`；不要求宿主使用React。MapAdapter负责选中道路、渲染图层、高亮实体和fit extent；核心不要直接引用MapLibre对象。

## GIS UI验收

成功、空数据、不可达、缺历史feed、Qwen System-One禁用/失败/本地模型不可用、图未收敛、SUMO未完成、取消都有不同状态。结果卡区分`computed fact`、`simulation estimate`、`attention`、`assumed`。无模型依据的指标卡不显示0，而显示not available。

颜色只是辅助；图例带单位和范围。比较图使用相同色标/分母，不以两张独立自动色域夸大变化。table可回连map，导出保留所有限制/来源字段。没有在线底图也能用本地roads+districts完成演示。

## reference部署

一个由使用者启动的同源本地站点：`http://127.0.0.1:<port>`，前端 `/`，API `/api`，same-origin proxy。不是作者中心服务。机构可接自己的反向代理/认证；v1不建用户账号、RBAC、团队协作。

不要默认远程HTTPS页面直接fetch用户localhost；浏览器CORS/本地网络访问规则和证书需要特定宿主适配，非第一版默认方案。发包要说明：这是Web应用组件，不是浏览器扩展，不保证给任意在线城市网页注入按钮。

## 必须留在产品里的安全底线

绑定loopback、启动随机local session token（仅本机交付），no wildcard CORS+credentials；请求大小/文件数/ZIP展开比上限；路径canonicalization，阻止../、symlink逃逸；禁止XML外部实体和任意SQL/命令；用户提供的URL不直接变成SSRF代理；子进程参数数组，job workspace独立，cancel准确；渲染text而非任意HTML，防止source文档prompt injection影响权限；API key只在backend env，error也需redact。

离线模式测试拦截所有外部HTTP，包括tiles、字体、telemetry、model调用。导出默认剔除敏感原文和tokens。跨机构访问权限由部署方网关处理，说明未配置网关不得监听公网；这不是要求开发者代做机构IT。

## BYOK

默认off。用户显式开启Qwen System-One后由本地Core调用，前端显示使用的字段类别；不上传整张KG，不要求外部API。便宜LLM不能作为“错误自动修复者”操作服务器；只输出schema草案且经过同等校验。


<!-- SOURCE FILE: docs/08_TESTING.md -->

# 08 · 代码测试：测试的是计算和失败边界，不是截图有颜色

当前包已经提供可执行reference tests；生产测试由WP逐包新增。禁止把只有mock的测试目录叫端到端验证。

## 测试层和运行时机

`fast`: 单元/性质/小图oracle，任何PR运行，不出网、不收费。
`sumo`: 真binary小网络 before/after，CI必须安装pinned binary；缺binary是BLOCKED，不skip后仍发布。
`browser`: Playwright真实插件+本地API+真实结果，不用全mock页面替代。
`data`: frozen Helsinki extract/GTFS与公告匹配，读真实bytes；初次下载网络单独处理。
`local_system_one`: 手动/有GPU runner的CI，真实本地Qwen推理、真实policy入图、记录model revision/calibration/device/latency；无供应商API。
`outcomes`: synthetic独立oracle、公告核验、可获得独立观测；各level分开。
`release`: clean checkout重建、全闸门、产物hash、证据路径。

## 明确测试清单

### T-NET

单向与逆向不同；转弯禁止；桥与地面交叉不相连；并行边仅封指定lane/edge；封闭生效[start,end)；不在窗口no-op；指定class限制；未知class/edge拒绝；设施snap到入口/可用路段；断路与零travel-time区分；单位m/s、km/h转换；已知fixed-weight仅删边时最短路成本不能降低（**拥堵仿真有Braess情形，不应用此单调断言**）；圈外替代路径保留。

### T-KG

src/dst存在、类型符合ontology、无孤儿引用、ID去重不跨源误并、时间冲突、证据缺失标unknown；NEAR不提升成causal/dependency；公交road overlap区分候选/verified；无标签泄漏；same citypack重建ID与CSR一致。

### T-PPR

mass conservation、nonnegative、dangling、disconnected、single node、all-zero rows、zero seed拒绝、NaN/negative拒绝、alpha边界；CSR vs dense solve vs NetworkX小图一致；排序稳定；no-op delta=0；共享seed/policy/node-set hash；uniform row scale invariance；multi-relation Qwen System-One policy改变P；single-type应被归一化抵消；permuted policy负对照；达不到residual阈值报失败。

### T-SYSTEM-ONE

每个 question 的 instructions 含 relation 语义；batch key集合检查；Score非整数正确；Noul/Choice/Score按typed contract；probabilities归一/finite；loopback为默认；非loopback必须显式opt-in；server unavailable→BLOCKED_ENVIRONMENT；未知/未pin model fail明确；local response可缓存replay但mode不同；模型revision、Reflex commit、dtype/device/permutations、calibration hash进入provenance；option-order sensitivity与重复运行稳定性有测试；rules fallback不标成local-qwen。浏览器bundle不直接访问模型服务。


### T-ONTOLOGY

ontology manifest version/type唯一；Object/Link/interface compatibility；authoritative snapshot hash在Action后不变；Action precondition/atomic commit/replay；assumed不能升级为observed；LLM不能绕过Action validator；ProjectionSpec不允许审计对象污染PPR；Object View facts与ResultBundle一致；action log/export可复现。

### T-COMPETITION / REPRODUCTION

feature matrix每格有source/date；unknown不自动写no；外部repo smoke只记录真实版本/命令/失败，不修改对方代码使其“看起来可跑”。性能比较必须记录同硬件/同输入；任务不等价时只做功能/architecture比较。

### T-SUMO

hard closure不允许无绕路车辆穿越；同class例外只来自用户；多closure无reroute循环；unfinished/teleport计数；shared seeds和demand；无route错误吞掉；取消、输出限额、相同baseline一致。

### T-WEB/API

两宿主加载同产物、卸载不漏listener；选图层→scenario→run→查看entity→export；失败/取消恢复；schema未知字段拒绝；本地token；路径穿越、恶意ZIP、SSRF、XSS拒绝；离线无HTTP；不同run目录不串结果；reference单worker不存在同SQLite写入死锁。

## 不以覆盖率替代正确性

覆盖率作为遗漏提示，核心network/PPR/contracts可设置branch>=85%为项目目标，但上面关键反例全部必须有assertion。至少对以下mutation做kill测试：反转方向、忽略end时间、把soft closure当hard、删除dangling处理、Qwen System-One不入P、忽略未到达、把mock改成local-qwen-pass。每个mutation必须被相关test挡住。

## 独立性

oracle不import生产ranker/router内部实现；生产输出CSV与oracle独立比较。参考小图可手算/穷举，实城不是靠模型自评。修改oracle只能为修正证明过的错误，留下review记录，不能迎合生产结果。

## 性能目标

以开发机CPU/RAM/OS、节点/边数、OD量、seed、缓存状态为基准实测。参考目标：20万semantic edges的PPR在30秒内、peak RSS<4GB，属于待验证工程预算；超出先profile并修batch/representation，再讨论优化，不能凭感觉上GPU。SUMO预算独立，不承诺whole-city seconds。browser按渲染对象量和payload大小实测，topK展示不等于分析漏掉硬检查设施。


<!-- SOURCE FILE: docs/09_VALIDATION_ABLATION.md -->

# 09 · 成果验证与消融：证明有用，不强迫正结果

## 首先防止循环验证

把已输入的“封闭道路列表”再预测出来只能验证转换与约束执行；不是预测成功。把“哪些公交受影响”的官方名单先写入KG又当标签，会泄漏。把SUMO结果用作graph seeds，再用同SUMO结果证明Qwen System-One“发现影响”，最多是受控检索评估，不能声称独立现实准确率。

评估设置分开：
- **pre-screen**：仅知closure/network/既有关系，预测需检查哪些实体；oracle routing/SUMO affected set作为隐藏任务真值。注意固定关键设施不允许被模型筛掉。
- **post-analysis retrieval**：已有facts，判断是否找全与问题有关证据。标签应衡量资料检索，不声称物理预测。

每份实验写明自己的设置。

## 预注册数据分组

Synthetic：至少12个有独立答案的拓扑母题（双路、单桥、孤区、反向、换乘、同层/跨层、时间边界、车辆类别、数据缺失、零扰动、候选噪声、多关系）。每个4个参数变体，共48个scenario，按母题/走廊分组划train/dev/test，不能把几乎相同seed变体拆到两边当泛化。

真实R1：Helsinki CityRun公告、实体匹配、当前或历史snapshot明确区分。
真实F1：Kalasatama真实地点+显式assumed限制，直到补齐历史管制证据。

主结果先synthetic heldout与真实source replay。独立历史traffic observations缺失时V3不打分，不能用randomTrips补成“observed”。只两次真实事件不足以推广全欧洲。

## 对照矩阵

| ID | 路由/SUMO | 语义关系 | 图排序 | Qwen System-One | 检验什么 |
|---|---|---|---|---|---|
| A0 | 相同 | 无检索KG | 直接可达性/几何候选 | 无 | 纯GIS已能解决多少 |
| A1 | 相同 | typed KG | bounded reachability/explicit rule | 无 | 语义关系的增量 |
| A2 | 相同 | 同一KG | fixed typed PPR | 无 | diffusion增量 |
| A3 | 相同 | 同一KG | Qwen-System-One-conditioned typed PPR | 真实本地冻结policy | Qwen System-One增量 |
| A4 | 相同 | 同一候选事实 | 固定候选的Qwen System-One相关性排序，无PPR | 真实本地 | 是否其实不需要PPR |
| A5 | 相同 | 同一KG | neutral / permuted type weights PPR | 重用同一冻结policy，不重复本地推理 | 是否权重语义真的有效 |

primary contrast A2→A3；A0→A1、A1→A2、A4→A3为解释对照。不要对48scenario×所有alpha×多模型×城市全排列。先一个冻结profile+seed，再只对dev最敏感参数做有限敏感性（alpha0.7/0.85/0.95；epsilon0.1与0.25），test只跑选定配置一次；更改后新版本有记录。

## 指标

代码与routing：constraint violations必须0；mandatory facility check coverage100%；unknown/missing另外计数。
检索：Recall@10/20（有不足候选时同时报N与K）、MRR/nDCG仅有独立graded labels时，coverage按节点类型分层；topK为空/全负样本定义清楚。
固定网络：路径长度/时间与独立oracle误差、不可达precision/recall。
SUMO：paired travel-time delta、arrived/unfinished、队列变化，分别表明synthetic或measured。
Qwen System-One：有效响应率、本地模型调用量、输入长度/forward passes/实际wall-time与显存、cache hit、重复性；概率校准只在充分独立标签上诊断。
工程：wall time、CPU、peak RSS、artifact大小、冷/热缓存；图只跑一次却每模式重复计费是不允许的。

按scenario/group输出原始指标，使用paired difference和按scenario聚类的区间；小样本只报告描述性区间，不吹统计显著。地区/低数据类型的漏检也报告，不能只报全局平均。

## 不操纵效果阈值

工程必须：A3真正用到Qwen System-One；数学和功能正确；本地compute有账本；A0–A5可重复。
研究不强制：A3必须优于A2。如果A3无增益/变差，默认UI可保留A2，A3作为明确experimental选项，完整功能仍保留并如实写报告。不能为了漂亮PR删难案例或扩大prompt直到命中test。

## 真场景检验模板

R1 source replay：公告事实条目总数、可定位条目、方向正确数、precision of geometry review、time coverage、未确认车种/时间。人工review图和来源片段索引，而不是只附地图截图。

F1：verified incident facts、assumed restrictions名单、run覆盖的设施/网络、不支持的烟火/楼层分析、无法核验的响应时间。火灾公共位置不等于公开全部应急数据。

如获得观测：固定事件时段、前后/同星期控制日，检查weather/traffic baseline变化；校准与测试隔离，报告缺失计数器/定位误差/未观测路段。不保证这些数据能取得。

## 成果报告必须包括

comparison.csv/parquet、variant config、sample counts、split hashes、raw metrics、System-One policy/model hashes、negative findings、source/evidence cards、reproduce command、known limitations。结果不只放README的漂亮图。


## 外部项目比较不是A6

A0–A5仍是因果最清楚的内部实验。Urban Flow/TWA/CReDo/rescuePY/SUMO_LLM_Agent/FireCom 不增加成同一“总分A6”，因为任务、数据、校准和输出不同。按照 `docs/15_COMPETITIVE_BENCHMARK.md`：v1 完成功能矩阵、工程性能基线、至少一个可运行邻居的reproduction notes；论文阶段再增加1–2个共享子任务的公平外部基线。

新增 ontology ablation（不新增编号，嵌入A1/A2）：比较 `raw graph joins` 与 `typed operational ontology projection` 的 invalid relation rate、evidence trace completeness、scenario replay success，不能只看排名。


<!-- SOURCE FILE: docs/10_EXECUTION.md -->

# 10 · Codex 大步推进协议：8 工作包、54 goals、6 有界loops

## 大步的含义

一次交付完整能力而非一次写一个文件。每个WP包括contracts/实现/测试/运行样例/证据，默认直接从一个WP推进下一个可执行WP。不得“先研究几周，再逐个建空目录”。允许WP1数据核查与WP2算法工作并行，WP5前端在API契约冻结后并行。

依赖图见execution/work_packages.json。任务规模是工程分组，不是承诺某几周一定完成。

## 六个Loop

### L0 — bounded evidence acquisition
输入source registry；一次主入口+一次替代官方入口。每项至多两轮实质访问；失败记录HTTP/DNS/权限/日期覆盖，不换同义词无限搜。输出verified bytes或BLOCKED_SOURCE；能用current-network就明确标注，不编历史。

### L1 — large vertical implementation
读取active WP required docs→锁契约与验收→实现完整链→跑focused tests→生成demo artifact→更新STATE。只在module契约变动或WP边界跑全套昂贵测试。没有代码/测试产物的规划不算iteration成果。

### L2 — hypothesis-driven repair
每轮给出failure signature、具体因果假设、最小观测、patch、前后test输出。相同失败最多3轮，第三轮未解决转为缩小复现/独立review并明确阻塞下游；不得清空测试、放宽阈值、无限依赖重装。

### L3 — local Qwen System-One integration
先检查本地模型缓存/device/Reflex版本pin→启动本地 `/v1/systemone`→一次真实smoke→严格parse→真实图policy→保存model/config/calibration hash→cache replay。默认拒绝非loopback endpoint；模型不可达时继续rules/fixed-PPR目标，但全v1的Qwen gate保持 `BLOCKED_ENVIRONMENT`。不得把mock/replay当真实模型。

### L4 — ablation evaluation
固定data/split/facts→一次计算physical→A0–A5复用→独立评估→只在dev诊断→冻结→test最终一轮→报告正/负结果。相同输入policy cache复用，不循环让模型“优化回答”。

### L5 — integration/release
干净环境→build→fast→SUMO→browser→realcity→local-Qwen manifest→ablation→security/export→checksum→gate。证据缺失单独列，全部must gate PASS才engineering_complete；测量验证单独claim。

## 上下文与token纪律

初次读AGENTS+product+execution；之后只读activeWP和共享type diff。不要每一轮把MASTER_PLAN全文给模型。状态文件最多约150行，长日志在artifacts；失败报告截关键stack+repro，不贴几万行。

不做多模型“交叉投票”判断代码对不对。用test、oracle、mypy/tsc、浏览器测试。Reviewer只看验收指标、diff和失败证据，不让三个agents各自重新写完整方案。

至多3个实现worker并行，每个有不重叠的目录owner和返回格式；契约/lockfile只有integrator改。代码代理运行token按工具实际usage记账，无usage则unknown，不造精确数。项目System-One本地算力账本和Codex编程token账本分开。

## 每次handoff只写

`WP/GOAL状态 | 本次可运行产物 | 执行命令与退出码 | 失败/blocked根因 | 剩余budget | 下一个完整WP`。

缺少本地GPU/模型缓存/数据等环境信息只记录一次blocked，绝不在每步重复问城市/架构/是否3D。用户已选择Web、本地、Road&Fire、Qwen System-One+KG+PPR全v1，保持不变。

## 暂停规则不是半成品借口

本地模型/硬件或源数据阻塞时完成所有不依赖部分；精确列出剩余release gates。恢复后从STATE执行剩余门槛，不重写已经验证的模块。发现scope爆炸先删非v1能力，不删required本地Qwen System-One/graph/fire真实运行。


<!-- SOURCE FILE: docs/11_RELEASE.md -->

# 11 · 发布闸门与“第一版全部正常运作”

## 必须gate

GATE-CONTRACTS：schema/OpenAPI/TS一致，时间/单位/有向道路转换完整。
GATE-NETWORK：独立router反例、城市限制/设施接入、不可达处理。
GATE-GRAPH：typed temporal KG真实构建，来源与ID审计，非空实际关系。
GATE-PPR：CSR/dense/NetworkX一致，delta可比较，Qwen System-One影响路径测试。
GATE-QWEN-SYSTEM-ONE：真实本地Qwen/Reflex HTTP成功、精确model+revision+device/dtype/permutations+calibration provenance、真实graph应用policy。mock/replay/skip不能通过；缺本地模型或硬件为BLOCKED_ENVIRONMENT。
GATE-SUMO：真实binary paired-run及hard closure/unfinished统计通过。
GATE-WEB：两个宿主、地图选取/进度/取消/解释/export闭环。
GATE-REAL-CITY：Helsinki真实bytes被下载、hash/许可/coverage和道路公告映射审计；fire事实/假设分离且真实地点情景运行。
GATE-ABLATION：A0–A5可复现，独立labels/无泄漏、负结果允许，成本/耗时表。
GATE-SECURITY：no secret/egress-off/安全输入/jobs隔离，安全限制显示。
GATE-REPRODUCE：clean checkout命令、lockfile、container固定、结果manifest可重放。

附加claim：`historical_numeric_prediction` 只有独立历史观测充分才能VERIFIED，缺失为NOT_VALIDATED，不与工程gate混淆。一般GIS v1完成可不具备此claim，但宣传不得隐去。

## evidence manifest

每gate字段status(PASS|FAIL|NOT_RUN|BLOCKED_ENVIRONMENT|BLOCKED_EXTERNAL)、producer、commit、commands[{command,exit_code}]、evidence_files[{path,sha256}]、executed_at、scope。PASS必须有真实证据文件，schema脚本只做必要检查，不证明文件内容真实；CI和review必须检查内容，不得生成文字写“通过”代替日志。

`evidence/product_release.json` 初始所有NOT_RUN；`scripts/check_release.py` 返回非零。WP7更新路径哈希并用CI独立运行。

## clean checkout使用体验

维护者提供 `make bootstrap`, `make demo-offline`, `make test-*`, `make release-check`。离线demo先有已构建image/deps和本地小数据包才能真正不出网；首次安装依赖需要网络要在README写清，不作绝对离线营销。

产品ZIP含配置、版本、操作录像/截图、报告而不是密钥/个人信息/整份新闻。city data只在许可允许时分发，否则附fetch manifest；GitHub不塞大城市原始文件。

## 最终release notes

“完成Road & Fire GIS v1；验证级别为[逐项]。Qwen System-One integration[真实/阻塞]。历史交通数值验证[有/无]。火灾为[外部限制情景/真实管制复现]。不可用于实时调度或安全撤离。”

没有成功真实本地 Qwen System-One inference 就不能写括号里“默认禁用但已经完成”；缺证据就发布pre-release/incomplete状态。不能让强大的UI掩盖未接上的引擎。


## Operational ontology gate

发布前必须：
- ontology manifest versioned并通过schema/codegen一致性；
- authoritative snapshot在scenario Action前后hash不变；
- Road/Fire修改只能由typed Actions进入overlay；
- ActionRecords可重放得到相同scenario hash；
- Object View能展示对象状态/links/facts/attention/evidence/actions；
- PPR使用显式ProjectionSpec；
- feature comparison matrix完成且source可追溯；
- 至少一个外部OSS邻居有真实reproduction note；失败也可接受，但不能伪造成功。


<!-- SOURCE FILE: docs/12_RISKS_DECISIONS.md -->

# 12 · 风险与固定决策

| 风险 | v1处理 | 不允许的替代 |
|---|---|---|
| 没有历史GTFS/流量 | current-network what-if标记，历史数值NOT_VALIDATED | 当前feed假装历史 |
| 没有真实火灾警戒区 | 人工假设区明确记录 | 按severity捏造半径 |
| Qwen System-One本地模型/硬件不可用 | rules继续、local-Qwen gate blocked | mock说local模型完成 |
| Qwen System-One不带来增益 |保留真实backend，fixedPPR可作默认，发负结果 | 改标签/只留赢的案例 |
| 图只存道路没有语义 |必须跨road-route-facility关系与来源 |把OSM图改名KG |
| 大图/仿真慢 |CSR/cache/受控job/boundary测试 |先上集群/GPU |
| 数据少地区排名低 |coverage/unknown独立显示、必查设施不裁掉 |低置信度×0等于无影响 |
| 入图方向/层混乱 |ontology + direction fixture |全部无向PageRank |
| 稀疏type重权重不起作用 |测row normalization反例 |加噪声伪造Qwen System-One有用 |
| 用户以为消防响应可预测 |network travel time和实际response分开 |用速度×距离称response准确 |
| 机构服务器需求 |稳定API/executor seam/compose参考 |作者代运维账户系统 |
| 通用插件框架膨胀 |只一个插件、少量接口 |plugin商城/DSL语言先行 |

## 架构决策日志要求

每个重要改变写1页ADR：原决定、实测证据、替代方案、影响的schema/tests/消融可比性。不能以“未来扩展可能用到”为由加生产依赖。

## 增长路线（明确不是本轮）

后续Building Works可复用Restriction和external-effects contract；FDS/CFD、3D contextual enhancement、其他城市、NGSI-LD特定平台适配、multi-tenant、安全认证产品都不提前实现。当前v1完成是停止条件，而不是无限加新功能的起点。


<!-- SOURCE FILE: docs/13_JEV_TO_QWEN_MIGRATION.md -->

# 13 · Jev → Qwen System-One 迁移说明

核查日期：2026-09-23。[S22–S24]

## 为什么迁移

UrbanImpact GIS v1 不再把 TypeSafe Jev 的账号、注册、API key 或 hosted endpoint 作为任何发布前提。System-One 层改为部署方可本地/自托管的 **Qwen System-One**，参考实现为 `kshetrajna12/reflex` + `Qwen/Qwen3.5-4B`。[S22][S23]

## 哪些不变

- Road/Fire GIS、SUMO、typed temporal KG、PPR/Δ-PPR、Web plugin 范围不变。
- System-One 仍只做 soft semantic relevance，不触碰路权、速度、OD、火灾范围、物理指标。
- A0–A5 消融逻辑不变：A3 现在代表真实 Qwen-System-One-conditioned PPR。
- DeepSeek / GPT-5.6 Luna 等廉价 LLM 仍是可选 `LanguageBackend`，默认关闭、BYOK，用于场景草稿解析/歧义解释/文字说明。

## 哪些改变

1. `GATE-JEV/LIVE-PROVIDER` 全部替换为 `GATE-QWEN-SYSTEM-ONE`。
2. 不再检查 TypeSafe key/token/billing；改为检查本地/私网模型、revision、device/dtype、permutations、calibration hash 和真实 graph transition hash。
3. runtime 默认只允许 loopback；机构内网 GPU endpoint 需要显式 opt-in，并记录 egress scope。
4. 参考实现需要单独的模型运行环境；当前 Reflex 4B 发布路径文档指向 16 GB CUDA GPU。[S22] 缺 GPU 时允许继续所有非依赖工作，但 release gate 必须保持 `BLOCKED_ENVIRONMENT`，不能用 mock 或 rules 顶替。
5. 首次下载模型权重可需要联网；正式离线部署应预取并固定模型 revision。运行期不要求把城市数据发送给外部 AI。

## 为什么选 Reflex 作为参考而不是绑定它

Reflex 提供与 Jev 风格一致的 `POST /v1/systemone` typed contract，并明确支持 Choice/Score/Noul，不输出自由文本；其仓库 MIT，默认 Qwen3.5-4B 权重 Apache-2.0。[S22][S23] UrbanImpact 只依赖自己的 `QwenSystemOneBackend` 协议层，未来可换其他 Qwen System-One scorer。

另一个 `pngwn/system-one-qwen3.5-4b-scorer` 适合做研究对照，但当前模型卡为 CC-BY-NC-4.0，因此不作为主发行依赖。[S24]

## Codex 的迁移验收

必须证明：

- `make test-systemone-contract`：typed request/response fail-closed；
- `make test-systemone-local`：真实 Qwen 本地/私网模型推理，而非 mock；
- 多 relation fixture 中真实 Qwen score 改变 transition matrix；
- Helsinki scenario graph 消费真实 policy 并保存 `applied_transition_hash`；
- A2 vs A3 共用同一 physical facts，不能因为换模型重跑/篡改 SUMO；
- 校准/排序结果可以是负结果，A3 不要求胜过 A2；
- 无真实 inference 时发布状态必须是 `BLOCKED_ENVIRONMENT`。


<!-- SOURCE FILE: docs/14_OPERATIONAL_ONTOLOGY.md -->

# 14 · CiviFlux Operational Ontology：借鉴 Palantir 的“对象—关系—动作—函数”思想

更新：2026-09-23。本文是 GIS v1 的**规范性补充**。它借鉴 Palantir Foundry Ontology 的公开概念，但不复制 Palantir 代码、私有 schema 或 API，也不要求 Palantir/Foundry 才能运行。CiviFlux 必须保持开源、平台无关、data-local。

公开参考：
- Palantir Ontology core concepts: https://www.palantir.com/docs/foundry/ontology/core-concepts
- Object/link/action/interface type reference: https://www.palantir.com/docs/foundry/object-link-types/type-reference
- Action types: https://www.palantir.com/docs/foundry/action-types/overview
- Action consistency: https://www.palantir.com/docs/foundry/action-types/consistency-guarantees
- Action log: https://www.palantir.com/docs/foundry/action-types/action-log
- Functions on objects: https://www.palantir.com/docs/foundry/functions/functions-on-objects

## 1. 为什么要改：KG 不应只是 PPR 的临时输入

原方案中的 typed temporal KG 已经能做 graph diffusion，但如果只把 KG 当成“为了 PageRank 临时建的一张图”，产品会停留在分析算法层。Operational Ontology 的目标是让同一套语义同时约束：

1. 数据如何进入系统；
2. Scenario 可以对什么对象做什么改变；
3. SUMO / routing / PPR / Qwen System-One 接收什么输入；
4. Web 插件如何显示对象、关系、证据和允许的操作；
5. 每次用户操作和模型计算如何留下可审计记录。

**Ontology 是产品 API 的语义层，不是图数据库品牌。** v1 不需要 Neo4j/RDF/OWL server；可以用 JSON Schema/Pydantic + Parquet/SQLite + CSR graph 实现。

## 2. 六个核心原语

### 2.1 ObjectType

真实世界实体、事件或分析对象的类型。v1 最小集合：

- `RoadSegment`
- `Junction`
- `TransitRoute`
- `TransitStop`
- `Facility`
- `Hospital`
- `FireStation`
- `District`
- `PopulationCell`
- `FireIncident`
- `RoadRestriction`
- `Scenario`
- `SimulationRun`
- `ImpactObservation`
- `EvidenceSource`
- `AnalysisPolicy`

`Hospital` / `FireStation` 可实现 `Facility` interface，不要求继承式数据库实现。

每个 Object 必须有：
`object_id, object_type, source_namespace, source_id, valid_time, provenance_refs, properties, geometry_ref?`。

权威输入对象与派生分析对象必须区分：
- `authoritative/imported`
- `user_assumed`
- `derived`
- `simulated`
- `model_scored`

### 2.2 Property

属性必须有类型、单位、时间语义和 provenance。不要把 `speed=30` 这种无单位裸值传播到分析层。

关键共享属性：
- `valid_from`, `valid_to`
- `evidence_level`
- `source_timestamp`
- `confidence_status`
- `geometry_ref`
- `scenario_id?`
- `run_id?`

### 2.3 LinkType

关系是有类型、有方向、有来源、有时间的。v1 至少：

- `ROAD_CONNECTS_TO`
- `ROUTE_USES_SEGMENT`
- `SEGMENT_USED_BY_ROUTE`
- `STOP_ON_ROUTE`
- `FACILITY_ACCESSED_VIA`
- `SEGMENT_ACCESS_TO_FACILITY`
- `DISTRICT_CONTAINS`
- `CELL_LOCATED_IN`
- `INCIDENT_OCCURS_AT`
- `INCIDENT_RESTRICTS`
- `SCENARIO_CONTAINS_RESTRICTION`
- `RUN_EVALUATES_SCENARIO`
- `OBSERVATION_ABOUT_OBJECT`
- `DERIVED_FROM`
- `SUPPORTED_BY_EVIDENCE`

不要自动创建“语义上不同”的反向关系。需要反向传播时明确注册反向 LinkType。

### 2.4 Interface / Capability

借鉴 Palantir interface 的思想，为不同 ObjectType 声明共同能力，而不是让 UI/算法写几十个 `if type ==`：

- `RestrictableNetworkElement`
- `RoutableNetworkElement`
- `AccessibleFacility`
- `EmergencyResponder`
- `ScenarioPerturbation`
- `EvidenceBearing`
- `SpatialObject`
- `TemporalObject`

例如 `RoadSegment` 实现 `RestrictableNetworkElement`；以后 `PedestrianLink` 也可以实现同一 interface，而不改 Action contract。

### 2.5 ActionType

这是此次升级最重要的部分。用户和 LLM **不得直接编辑 KG 或数据库字段**。它们只能请求经过 schema、precondition、permission-boundary、evidence 校验的 Action。

v1 ActionType：

- `CreateScenario`
- `AddRoadRestriction`
- `CreateFireIncident`
- `AttachImportedPerimeter`
- `AttachEvidence`
- `ValidateScenario`
- `RunScenario`
- `CancelRun`
- `CompareRuns`
- `ChangeAnalysisPolicy`
- `ExportResultBundle`

Action 只修改 **scenario workspace / overlay**，绝不修改部署者的 authoritative city source。

每个 Action 必须产生 `ActionRecord`：
`action_id, action_type, timestamp, parameters_hash, actor_context?, input_object_refs, precondition_results, output_object_refs, status, error?, provenance_hash`。

不做市政府账号体系，因此 `actor_context` v1 可以是 local session/client label；身份认证和组织权限由部署者基础设施负责。

### 2.6 Function / AnalysisFunction

函数读取 typed objects/links，返回 typed results；物理函数和语义函数必须分开：

**Deterministic / physical**
- `compileRestrictions()`
- `routeBaselineEvent()`
- `runSumoPair()`
- `computeAccessibilityDelta()`

**Graph / semantic**
- `projectScenarioGraph()`
- `computeFixedPPR()`
- `scoreRelationTypesSystemOne()`
- `computeConditionedPPR()`
- `explainWitnessPaths()`

LLM function 只能：
- `parseScenarioDraft()`
- `explainResult()`
- `proposeActionParameters()`

它不能直接提交危险 Action；最终必须走同一个 Action validator。

## 3. Baseline 不可变 + Scenario Overlay

不要像普通 CRUD 系统一样把道路状态改成 `closed=true`。采用：

```text
Authoritative City Objects (immutable snapshot)
                │
                ├── Scenario A overlay
                │      ├── RoadRestriction
                │      └── FireIncident
                │
                └── Scenario B overlay
```

`RoadSegment` 本身不被删除或覆写。某场景是否可通行由：

`effective_state(object, analysis_time, scenario_overlay)`

计算。

这让：
- baseline/event 比较严格可重复；
- 多个 scenario 互不污染；
- Action log 可以完整重放；
- PPR 的 node universe 能稳定；
- 导出时可以给出“原始事实”和“场景假设”的清楚差异。

## 4. Ontology → Scenario Graph，而不是 Ontology = PPR Graph

Operational Ontology 是完整语义模型；PPR 只使用其中一个 projection：

```text
Operational Ontology
   Objects + Links + Actions + Runs + Evidence
                 │
                 ▼
      ProjectionSpec(objective, time)
                 │
                 ▼
          Scenario Graph
                 │
        fixed / Qwen PPR
```

禁止把 `ActionRecord`, `EvidenceSource`, `SimulationRun` 等所有对象默认塞进 PPR；每个 projection 必须有明确 allowlist / edge direction / relation policy。

Projection 必须保存：
`projection_id, ontology_version, scenario_id, analysis_time, object_filters, relation_filters, relation_policy_hash, source_snapshot_hash, graph_hash`。

## 5. Object View：Web 插件围绕“对象”而不是围绕 dashboard

点击道路/医院/消防站/事件时统一显示 Object View：

1. **Identity**：ID、类型、来源、时间；
2. **State**：baseline 与当前 scenario state；
3. **Links**：关键依赖关系；
4. **Metrics**：routing/SUMO 事实指标；
5. **Attention**：fixed/Qwen PPR，不叫风险；
6. **Why**：witness paths + source/evidence；
7. **Actions**：该对象当前允许的 typed actions；
8. **History**：本 scenario 的 ActionRecords。

这会成为与“只有图层和指标面板”的交通 DT 的主要产品差异之一。

## 6. Action preconditions

示例 `AddRoadRestriction`：

- object implements `RestrictableNetworkElement`；
- edge 存在于 pinned citypack；
- valid time 合法；
- vehicle class 合法；
- restriction 不修改 authoritative source；
- evidence_kind 必须是 `observed|announced|assumed`；
- 若来自 LLM draft，必须用户确认；
- `assumed` 不能在 UI 显示为 observed。

示例 `CreateFireIncident`：

- 位置必须解析到明确 geometry 或用户确认 point；
- 不根据 severity 自动生成认证警戒半径；
- imported perimeter 必须有来源；
- assumed perimeter 明确标注 assumption。

## 7. Action atomicity / replay

借鉴“Action 是一次受控事务”的思想，但 v1 只在 CiviFlux scenario workspace 内保证：

- action record 先验证后 commit；
- 同一次 Action 产生的对象/links 全部成功或全部不提交；
- external side effect（SUMO job）不假装是数据库 ACID 的一部分；
- `RunScenario` 创建 immutable `SimulationRun`，运行失败保持 failure record；
- 所有 action 可通过日志重放生成同一 Scenario overlay hash。

## 8. Ontology versioning

`ontology/manifest.yaml` 是 v1 的语义 source of truth：

- ontology version
- object types
- interfaces
- link types
- action types
- function signatures
- projection specs

从 manifest 生成或一致性校验：
- Pydantic types
- TypeScript types
- JSON Schema
- OpenAPI fragments

不要维护四份手写 schema。

破坏性类型变化必须 bump major ontology version；新增 optional property/link/action 可 minor bump。

## 9. 与外部城市生态的 adapter 边界

CiviFlux Ontology 不是要替代：
- NGSI-LD
- CityJSON/CityGML
- The World Avatar ontology
- FIWARE
- EU LDT Data Platform

adapter 负责映射：

```text
external entity/context
        ↓ mapping + provenance
CiviFlux Object/Link
        ↓ scenario actions
CiviFlux analysis
```

未来可添加 `ngsi_ld`, `cityjson`, `twa_rdf` adapters，但 v1 核心只要求 GIS/OSM/GTFS/Helsinki。

## 10. 需要新增的测试

### T-ONTOLOGY
- object/link/action registry 唯一且 versioned；
- link src/dst/interface 合法；
- provenance/evidence required fields；
- derived object 不能冒充 authoritative；
- scenario overlay 不修改 baseline hash；
- action schema invalid inputs 被拒绝；
- action replay 得到相同 scenario hash；
- failed action 无 partial commit；
- direct graph edit API 不存在；
- LLM proposal 必须经 action validator；
- projection allowlist 保证审计对象不会污染 PPR；
- object view 的 metrics 与 ResultBundle 同源。

### Mutation tests
必须能挡住：
- 把 assumed 改成 observed；
- Action 绕过 validator；
- restriction 直接覆写 baseline RoadSegment；
- 将所有 ontology links 无差别投影进 PPR；
- 删除 provenance；
- replay 顺序错误导致 scenario hash 不一致。

## 11. v1 不做

- 通用企业 ontology builder UI；
- SPARQL/OWL 推理器；
- Palantir Foundry adapter；
- 跨机构 permission model；
- ontology marketplace；
- 自动把 LLM 生成的 relation/action 直接写入 authoritative data。

**第一版只做 Road & Fire 所需的 operational ontology 核心，并为未来插件复用。**


<!-- SOURCE FILE: docs/15_COMPETITIVE_BENCHMARK.md -->

# 15 · 竞争生态、机构背景与比较方案

更新：2026-09-23。目标不是宣传“没人做过”，而是明确 CiviFlux 的生态位、可验证差异与以后论文/README需要的公平比较。

## 1. 主要相邻项目与背后机构

| 项目 | 背后机构/高校 | 与 CiviFlux 重叠 | 主要不同 |
|---|---|---|---|
| EU LDT Toolbox · Urban Flow | European Commission DG CNECT；EU LDT Toolbox/CitiVERSE 体系，长期治理由相关 EDIC；早期技术规格工作由 Deloitte、Capgemini、OASC、Intellera、Technopolis、IMEC、TNO、DTU 等参与 | Web LDT、道路 what-if、微观交通仿真、路网/排放 | 重点是 traffic reconstruction/simulation；不是 Road+Fire 跨域 ontology / Δ-PPR 插件 |
| The World Avatar (TWA) | Cambridge CARES；起源于 University of Cambridge 相关团队与 NRF Singapore CREATE；协作者含 CoMo、CMCL、CMPG | dynamic KG、agents、city resilience、跨域模型 | 大型 persistent semantic DT ecosystem；CiviFlux 是轻型 scenario-local plugin，不要求迁移整个平台 |
| CReDo | Connected Places Catapult；起于 UK National Digital Twin Programme / Centre for Digital Built Britain (University of Cambridge + UK government)；基础设施伙伴含 UK Power Networks、Anglian Water、BT，后续还有 STFC、National Grid、University of Edinburgh 等 | cross-sector dependencies、cascade、digital twin、climate resilience | 主域是 energy/water/telecom/weather；不是道路/消防运行插件 |
| rescuePY / Munich emergency DT | Technical University of Munich, Chair of Automotive Technology；Munich Fire Department；BMFTR M-Cube/DatSim2.0 | emergency vehicles、traffic、SUMO/pgRouting/PostGIS、what-if | 深入应急响应系统和实车数据；缺少通用跨域 ontology + graph diffusion plugin layer |
| AI-Reinforced Traffic Digital Twin (NYC) | NYU Tandon C2SMART；New York City Fire Department (FDNY) | ambulance/emergency response、traffic DT、AI、真实校准 | 专注 EMV 速度/干预优化，不是开源城市 disruption ontology plugin |
| SUMO_LLM_Agent | The University of Texas at Austin；Yiming Xu、Jihyung Park、Junfeng Jiao，NeurIPS 2025 UrbanAI Workshop | Web+SUMO+LLM、road edits、incidents/work zones/special events | 自然语言控制仿真是核心；没有 ontology-driven cross-domain impact + Δ-PPR |
| FireCom | UT Austin Urban Information Lab + Texas Advanced Computing Center + Austin Fire Department / Homeland Security Emergency Management；另有 Cornell Tech 等合作者 | urban fire DT、GIS、real-time fire/smoke、public dashboard | 强项是 fire/smoke/exposure；CiviFlux v1 不做 CFD/烟羽，做火灾引起的外部网络/服务影响 |

来源入口：
- EU Urban Flow: https://interoperable-europe.ec.europa.eu/collection/ldttoolbox/solution/urban-mobility/solution-overview
- EU LDT project: https://interoperable-europe.ec.europa.eu/collection/ldttoolbox/news/introduction-eu-local-digital-twin-toolbox-project
- TWA: https://github.com/cambridge-cares/TheWorldAvatar ; https://www.cares.cam.ac.uk/research/the-world-avatar/
- CReDo: https://cp.catapult.org.uk/project/climate-resilience-demonstrator-credo/
- TUM rescuePY paper: https://www.mdpi.com/2624-6511/9/2/36
- NYC/FDNY TDT: https://doi.org/10.1007/s42421-026-00166-4
- SUMO_LLM_Agent: https://github.com/xuyimingxym/SUMO_LLM_Agent
- FireCom: https://pubmed.ncbi.nlm.nih.gov/41078483/

## 2. CiviFlux 必须守住的差异

### D1 · Plugin, not platform
能嵌入既有 Web Digital Twin；不要求城市把数据迁移进作者运营的平台。

### D2 · Disruption intelligence, not generic visualization
核心输入是事件/限制；核心输出是 before/after 事实、跨域依赖和 criticality shift。

### D3 · Operational ontology, not passive KG
Objects + Links + Actions + Functions + Evidence + Object Views。用户修改 Scenario 必须走 typed actions，不能直接 CRUD 图节点。

### D4 · Scenario-local graph, not mandatory mega-KG
普通 GIS/OSM/GTFS 就能运行；只为当前 objective/time 投影相关 semantic graph。TWA/NGSI-LD/CityJSON 是可选 adapter。

### D5 · Physical facts and semantic attention separated
SUMO/router 负责 travel time、queue、reachability；PPR/Qwen 负责 relevance/attention。图算法不冒充交通、火灾或因果模拟。

### D6 · Criticality Shift, not static centrality
保持同一 node universe / seed / policy，比较 baseline/event；单独区分 policy ablation。

### D7 · Road + Fire coupled external impacts
既看 road closure，也看 fire-induced restrictions 对 emergency response / transit / facilities 的共同影响；不重造火灾 CFD。

### D8 · Progressive enrichment
Tier 0 OSM 可运行；GTFS、population、traffic detectors、NGSI-LD、3D/BIM 逐级增强，3D 不是依赖。

### D9 · Data-local OSS
无作者中心云、无强制账号/AI、机构服务器由部署者自己运维。

### D10 · Evidence-first
每个对象、link、restriction、metric、model score 都能追到 source/assumption/run，Fire 场景事实和假设严格分离。

## 3. 功能比较：v1 必须做

发布文档维护 `comparison/feature_matrix.csv`，至少包含：

- road closure what-if
- traffic microsimulation
- public transit linkage
- emergency response linkage
- fire external impact
- smoke/fire physics
- typed ontology
- scenario actions
- persistent KG requirement
- scenario-local graph
- graph ranking/diffusion
- baseline/event criticality delta
- AI scenario parsing
- AI relation scoring
- self-host/data-local
- Web embeddable component
- 3D mandatory/optional
- provenance/action replay
- open-source license

规则：
1. 只根据公开文档/实际运行结果填 `yes/no/partial/unknown`；
2. `unknown` 不能推断为 no；
3. 不给项目打总分，不造“冠军”；
4. 每格可追溯来源和检查日期。

## 4. 性能比较：不要做伪公平排行榜

### v1 必须有：内部工程性能
同一机器、同一 citypack/graph/scenario：
- citypack import time / peak RSS
- restriction compile latency
- deterministic routing pair latency
- semantic projection nodes/edges/time/memory
- fixed PPR latency/convergence
- Qwen relation scoring latency/device/memory
- Qwen-conditioned PPR latency
- SUMO wall-time / simulated-time ratio
- ResultBundle size
- Web initial load / result payload / interaction latency

### v1 必须有：内部效果基线
A0–A5 是主比较：
- top-K recall of hidden affected objects
- NDCG/MRR where ranking labels exist
- evidence retrieval precision/recall
- no-op false positives
- graph truncation stability
- calibration metrics for Qwen System-One where appropriate

### 外部性能比较：只在公平时做

**可以直接运行/共享任务时**：
- `SUMO_LLM_Agent`: 比较 scenario authoring success、schema invalid rate、execution reproducibility；不要拿它的 LLM latency 和 CiviFlux graph speed混成一个数字。
- Urban Flow：只有能获得相同 network/flow observations 和公开 reproducible pipeline 时才做 traffic-output/runtime 子任务比较。它的 detector-based route reconstruction 与 synthetic demand 是不同问题，不能直接宣称谁更准。
- rescuePY：若公开代码/数据允许，用同一 road/emergency-response 子任务比较 route/response analysis；否则做 architecture/function comparison。
- TWA/CReDo/FireCom：域和数据模型差异大，默认做功能/architecture/case-study comparison；除非建立明确共享 benchmark，不做“速度谁快”。

## 5. 论文型比较建议

论文主问题不是“CiviFlux 是否比所有产品强”，而是：

> 在同一个 urban disruption scenario 中，加入 operational ontology + typed cross-domain graph + scenario-conditioned diffusion，是否比纯 GIS/SUMO、规则关系、固定 PPR 或 System-One-only 更好地发现/组织与事件相关的跨域对象与证据，同时保持物理事实不被 AI 改写？

主实验：A0–A5 + synthetic held-out + Helsinki source replay + 若能获得独立历史观测则额外 numerical validation。

外部项目用于：
- 证明需求和相邻生态成熟；
- 解释产品差异；
- 在少数共享子任务做可复现实验；
而不是强行把所有系统变成同一 benchmark。

## 6. Palantir-inspired ontology 如何成为产品差异

不要宣传“我们有 Palantir Ontology”。正确表述：

> CiviFlux uses an open operational ontology inspired by object-centric decision systems: typed urban objects and links, controlled scenario actions, deterministic/model functions, evidence lineage and object-centric views.

价值在于：
- RoadRestriction 是对象，不是散落的 JSON patch；
- FireIncident 是对象，和其假设/证据分开；
- `RunScenario` 是 Action，不是随便调用脚本；
- SimulationRun 和 ImpactObservation 可审计；
- 同一个 Action contract 可以被 Web UI、LLM、未来 EU LDT adapter 重用；
- 插件族（RoadFire / BuildingWorks / LargeEvents）共享 ontology interfaces 和 perturbation primitives。

## 7. 比较结果何时进入 release gate

GIS v1：
- 功能矩阵必须完成；
- 内部 A0–A5 与工程 benchmark 必须完成；
- 至少一个可运行外部 OSS 邻居完成 smoke/reproduction notes（优先 SUMO_LLM_Agent）；
- 不要求为了 v1 强行复现 TWA/CReDo/FireCom 全栈。

准备论文/正式 research release：
- 增加 1–2 个公平共享任务的外部基线；
- 报告硬件、数据、版本、失败场景；
- 不根据 benchmark 结果临时修改 held-out labels 或删除失败案例。


<!-- SOURCE FILE: execution/GOALS_AND_LOOPS.md -->

# 8个大工作包 / 54 goals

每个WP一次推进完整能力；goals用来验收，不要求54轮对话。

## WP0 一次打通工程骨架、契约、toy运行与Qwen System-One预检
前置：[]。Prompt：prompts/01_WP0.md

- **G001** 建立可运行monorepo与锁文件：Python API、TypeScript component构建，版本/许可可追溯，不只空目录
- **G002** 冻结Scenario/Result/KG契约：JSON Schema/Pydantic/TS一致性测试与无效输入拒绝
- **G003** 贯通toy纵向运行：scenario→route facts→graph→PPR→ResultBundle，从API可取实际数值
- **G004** 真实Qwen System-One环境预检：检查本地Reflex/Qwen endpoint、模型/commit pin、device与calibration；能跑则真实smoke；不能则精确BLOCKED_ENVIRONMENT
- **G005** 测试与命令入口：创建make与CI层级，参考oracle与产品tests隔离
- **G006** 记录状态和边界：STATE、能力清单、初始release manifest无假PASS

## WP1 Helsinki真实citypack与两个事件证据落地
前置：['WP0']。Prompt：prompts/02_WP1.md

- **G101** 下载并冻结OSM/GTFS：真实bytes+sha256+日期+license；失败不伪造fixture
- **G102** 构建标准实体与路网映射：稳定ID、方向、连接、设施入口、source lineage
- **G103** 核验公交feed覆盖和shape匹配：calendar>24h、historical/current分开，ambiguous仅candidate
- **G104** R1公告有向路段映射：端点/方向review图和unknown hours字段
- **G105** F1火灾事实假设分离：日期街道已核验；精确坐标/cordon需source或assumption
- **G106** 锁数据评估边界：真实观测最多两轮检查、split/source manifests、missing-data report

## WP2 Road & Fire确定性GIS影响引擎完成
前置：['WP0']。Prompt：prompts/03_WP2.md

- **G201** 时间与车种限制编译器：半开时间窗、未知edge拒绝、direction/class准确
- **G202** 独立可达性与路由比较：turn-aware shortest paths、unreachable不为0
- **G203** 火灾外部限制输入：点/区/道路→需确认restrictions，不生成火灾physics
- **G204** 设施与公交影响facts：入口/route match分级、必查设施不被topK裁掉
- **G205** 边界与不完整数据处理：扩大network验证、缺失指标不假0
- **G206** oracle和反例全覆盖：单向/唯一桥/转弯/平面交叉/无事件/权限反例

## WP3 typed KG + 固定PPR + 真Qwen-System-One-PPR完成
前置：['WP0', 'WP2']。Prompt：prompts/04_WP3.md

- **G301** 真实typed temporal KG投影：跨道路/公交/设施、provenance、方向和窗口审计
- **G302** CSR PPR及独立oracle：mass/residual/dangling/alpha，dense+NetworkX一致
- **G303** paired delta可比较：相同U/s/alpha/policy hashes，no-op=0
- **G304** 真实Qwen System-One协议与pipeline：Score批量→合法policy→真实图PPR，缓存/本地endpoint/model revision/calibration/性能记录
- **G305** 解释路径和类型内显示：路径引用真实edge，attention不伪装risk
- **G306** 防装饰消融钩子：neutral/permute/no-PPR modes及单relation取消反例

## WP4 SUMO真正联调与paired仿真结果完成
前置：['WP1', 'WP2']。Prompt：prompts/05_WP4.md

- **G401** 真实binary安装和adapter：版本锁、命令数组、logs、资源限额
- **G402** network/demand映射：有向edge到SUMO映射，same demand/seed，synthetic标签
- **G403** hard closure/class运行：禁止soft误用，多rerouter loop反例
- **G404** before/after metrics：arrived/unfinished/teleported完整分母，real输出
- **G405** 取消和失败隔离：kill子进程、atomic产物、坏route不吞掉
- **G406** Helsinki代表场景可跑：bounded network和simulation coverage，未校准明确

## WP5 可嵌入Web GIS成品闭环
前置：['WP0', 'WP2', 'WP3']。Prompt：prompts/06_WP5.md

- **G501** 同一Web Component两宿主：MapLibre+vanilla，真正同build artifact，dispose不泄漏
- **G502** 地图→scenario→运行：道路/火灾输入、窗口/车种/assumption明确
- **G503** 进度取消失败体验：API真实job，不虚拟输出，不吞Qwen System-One错误
- **G504** 事实/attention/证据联动：before/after同标度，必查设施、why paths、模型状态
- **G505** 导出与重放入口：结果ZIP含完整manifest/metrics/sources，不含key
- **G506** local安全/offline：same origin/token、恶意输入拒绝、offline零出网

## WP6 成果验证、完整消融与性能成本报告
前置：['WP1', 'WP3', 'WP4', 'WP5']。Prompt：prompts/07_WP6.md

- **G601** 冻结48情景与独立labels：按母题/走廊split，模型无heldout访问
- **G602** 公平运行A0–A5：physical cache共享，real local Qwen System-One response冻结，负对照完整
- **G603** R1源事实复现审计：边界/方向/时间精度与公告对照，非数值准确性
- **G604** F1真实地点情景审计：incident事实与假设分开，不冒称实际管制/响应
- **G605** 如有观测则独立数值验证：取得才评估，否则NOT_VALIDATED，不停工空转
- **G606** 成本性能与负结果：raw metrics/置信区间适用性/预算/RSS/latency；无增益诚实报告

## WP7 干净环境发布验收与完整工程交付
前置：['WP6']。Prompt：prompts/08_WP7.md

- **G701** clean checkout重建：locks/container、文档命令实际可跑
- **G702** 全部must gates：contracts/network/KG/PPR/Qwen System-One/SUMO/web/realcity/ablation/security/reproduce
- **G703** 独立审查与mutation：关键错误必须被tests挡住，reviewer不伪称人类专家
- **G704** 许可隐私与数据分发：source attribution/SBOM/no secret/数据包许可单列
- **G705** 完成用户文档和演示：local安装、真实模式切换、限制/negative findings可见
- **G706** 准确声明完成与缺口：工程complete与measured validation分开，发布/推送需明确授权

## 六个Loop

L0证据获取，L1纵向实现，L2有限修复，L3真实本地Qwen System-One，L4冻结消融，L5集成发布。详见docs/10_EXECUTION.md。


## Operational Ontology / benchmark 新增验收目标（handoff-3）

- **G007 / WP0**：冻结 versioned ontology manifest 与 Pydantic/JSON Schema/TS 一致性。
- **G207 / WP2**：Road/Fire scenario changes 全部通过 typed Actions + overlay + replay。
- **G307 / WP3**：Ontology 通过 ProjectionSpec 生成 PPR graph，审计对象不污染 ranking。
- **G507 / WP5**：Object-centric Web View + Action UI，不提供任意 graph CRUD。
- **G607 / WP6**：source-backed competitor feature matrix + internal benchmark + 至少一个外部 OSS reproduction note。
- **G707 / WP7**：ontology/action/replay/projection 与竞争比较证据进入 release audit。


<!-- SOURCE FILE: execution/ACCEPTANCE_COMMANDS.md -->

# 产品命令契约（WP0建立，不是本包已实现）

| Target | 输出/失败语义 |
|---|---|
| make bootstrap | 根据锁文件安装，不静默升级；禁止echo成功替代安装 |
| make test-contracts / test-unit | 无网络、独立oracle，JUnit及实际exit code |
| make test-network / test-scenarios | 有向时空restriction与fire假设链 |
| make test-graph / test-ppr | ontology、lineage、数值残差、pair比较 |
| make systemone-preflight | 检查本地Reflex/Qwen服务、模型pin、hardware、calibration；缺失exit2并给BLOCKED_ENVIRONMENT |
| make test-systemone-contract | typed wire/mock parser tests，不充当真实模型 |
| make test-systemone-local | 真实本地Qwen System-One→真实graph；缺模型/硬件/服务exit2且阻塞full release |
| make citypack-fetch / citypack-build / test-data / case-review | 真bytes、manifest、日期与人工可审mapping |
| make test-sumo / demo-sumo-pair / test-cancel | 真binary，有日志和结果，缺binary不算通过 |
| make build-web / test-web / test-browser | 真browser+same component两host |
| make test-outcomes / ablate / benchmark / report | 原始指标、split、cost、negative findings |
| make clean-checkout-test / security-check / release-check | 全must gates，有任何required未运行则非0 |

make target可以包装uv/python/npm/docker，但不把source缺失或live跳过吞成0。fast CI可以有明确nonrelease mock suite，release CI不能因此变绿。


<!-- SOURCE FILE: prompts/00_MASTER.md -->

你现在是 UrbanImpact Road & Fire GIS v1 的交付负责人和实现工程师。不是继续给我建议，而是在当前仓库执行本工程包。

先读 AGENTS.md、README.md、docs/00_PRODUCT.md、docs/10_EXECUTION.md、docs/14_OPERATIONAL_ONTOLOGY.md、execution/work_packages.json、execution/STATE.md。已有仓库先检查git status和目录，不覆盖未提交工作。不要一次把所有文档注入上下文，后续按active WP读取。

最终必须交付：Web可嵌入GIS插件、Helsinki公开数据示例、Road/Fire外部网络限制、真实routing/SUMO、operational ontology + typed scenario graph、fixed PPR、真实Qwen-System-One-conditioned PPR、可追溯结果、代码测试、成果验证、A0–A5消融、可复现部署。

按WP0–WP7大工作包执行。每轮直接完成一条纵向闭环：实现→测试→实际运行→保存产物→独立验收，再进入下一个可运行工作包。不要只写计划、空类、TODO、mock UI后宣布完成；不要拆成“建一个文件后问我继续吗”的小步。

Qwen System-One 必须通过部署者本地 **Reflex + Qwen3.5-4B** 做真实推理，并让响应进入 graph transition 与 PPR；mock/replay 不能满足 release gate。没有 closed Jev provider 注册、API key 或按 token 付费。缺少本地模型、GPU/可用device、模型权重或服务时写 BLOCKED_ENVIRONMENT，继续所有非依赖任务；不得用规则fallback假装该gate通过。发布必须pin Reflex commit、Qwen revision、precision/device、permutations和calibration hash。机构服务器、多用户、账号、SSO、SaaS不属于本项目。

城市已选Helsinki；事件证据已放cases/sources，先验证真实bytes和日期覆盖，不重启无尽选城研究。当前GTFS不能装作历史时刻表；真实火灾地点加assumed cordon必须标记what-if；没有独立观测不称拥堵/消防响应预测正确。

从第一天把ablation做进接口：A0、A1、A2、A3、A4、A5共享输入/physical facts，Qwen System-One不准改速度、OD、权限或火灾安全半径。固定before/after比较的节点集合、seed、alpha、policy，保证delta有定义。默认模型不是政策决策者或消防调度器。

同失败最多3次假设不同的修复循环，外部来源最多2轮访问；每次要产出代码/test证据，不要重复讨论架构。需要并行且工具支持时最多3个独立worker，锁定文件owner，integrator独占契约/lockfiles；否则串行完成。不要制造虚拟agent对话。

现在从WP0开始，能继续就按依赖自动推进到v1 gate；每个WP只汇报：完成目标、运行命令/退出码、证据路径、真实阻塞、下个大工作包。token花在实现、测试和修复，不花在重复总结。不得自动push、公开部署或修改用户系统安全设置。

结束必须给出全部release gates和实际artifact清单；未完成不能改名成已完成。负消融结果允许，伪造进步不允许。


Ontology不是装饰层：authoritative city snapshot immutable；RoadRestriction/FireIncident/Scenario/Run/Evidence作为typed objects；用户和LLM只能通过typed Actions改变scenario overlay；Functions读取typed objects；PPR只运行在ProjectionSpec生成的scenario graph。实现并测试ActionRecord/atomic commit/replay/Object View。不得复制Palantir专有API；这是开放架构借鉴。

竞争比较按docs/15_COMPETITIVE_BENCHMARK.md执行：v1必须有feature matrix、内部A0–A5与工程benchmark、至少一个可运行外部OSS的reproduction notes。不要给不同任务系统强行总分排行，不要把unknown写成no。


<!-- SOURCE FILE: prompts/01_WP0.md -->

# WP0 · 一次打通工程骨架、契约、toy运行与Qwen System-One预检

你负责交付这个完整工作包，不是生成下一份计划。先遵守根AGENTS与总prompt。

## 只加载这些详细文档

- docs/00_PRODUCT.md
- docs/01_ARCHITECTURE.md
- docs/03_CONTRACTS.md
- docs/05_QWEN_SYSTEM_ONE.md

前置：无；检查仓库现状。允许外部blockers记录后并行不依赖工作，但对应release gate不可以PASS。

## 本批必须一起完成的goals

### G001 建立可运行monorepo与锁文件
验收：Python API、TypeScript component构建，版本/许可可追溯，不只空目录。
必须留下实际test/artifact，不以文字宣称完成。

### G002 冻结Scenario/Result/KG契约
验收：JSON Schema/Pydantic/TS一致性测试与无效输入拒绝。
必须留下实际test/artifact，不以文字宣称完成。

### G003 贯通toy纵向运行
验收：scenario→route facts→graph→PPR→ResultBundle，从API可取实际数值。
必须留下实际test/artifact，不以文字宣称完成。

### G004 真实Qwen System-One环境预检
验收：检查本地Reflex/Qwen endpoint、模型/commit pin、device与calibration；能跑则真实smoke；不能则精确BLOCKED_ENVIRONMENT。
必须留下实际test/artifact，不以文字宣称完成。

### G005 测试与命令入口
验收：创建make与CI层级，参考oracle与产品tests隔离。
必须留下实际test/artifact，不以文字宣称完成。

### G006 记录状态和边界
验收：STATE、能力清单、初始release manifest无假PASS。
必须留下实际test/artifact，不以文字宣称完成。

## 执行loop

L1完整实现；失败进入L2至多3次；Qwen System-One用L3、数据用L0，评估用L4。保护原始tests与independent oracle。

## 退出命令（若未建立命令，在WP0/当前包实现真实target，不能echo成功）

```bash
make bootstrap
make test-contracts
make test-unit
make demo-toy
make systemone-preflight
```

产物必须包含 `evidence/wp0/walking_skeleton.json`，记录commands/exit codes/artifact sha256/mode/scope。同步execution/goals.json、STATE.md。

## 自审必须问

是否实际调用了本包要求的外部/仿真能力？哪些仍是mock？哪些data只是current snapshot？有没有修改baseline/demand或label导致消融不公平？有没有新增非v1平台工程？

完成后返回实际交付/失败签名/可继续的下一WP，不重新询问已确定的城市/是否Web/是否本地。


<!-- SOURCE FILE: prompts/02_WP1.md -->

# WP1 · Helsinki真实citypack与两个事件证据落地

你负责交付这个完整工作包，不是生成下一份计划。先遵守根AGENTS与总prompt。

## 只加载这些详细文档

- docs/02_DATA_CASES.md
- docs/03_CONTRACTS.md

前置：WP0。允许外部blockers记录后并行不依赖工作，但对应release gate不可以PASS。

## 本批必须一起完成的goals

### G101 下载并冻结OSM/GTFS
验收：真实bytes+sha256+日期+license；失败不伪造fixture。
必须留下实际test/artifact，不以文字宣称完成。

### G102 构建标准实体与路网映射
验收：稳定ID、方向、连接、设施入口、source lineage。
必须留下实际test/artifact，不以文字宣称完成。

### G103 核验公交feed覆盖和shape匹配
验收：calendar>24h、historical/current分开，ambiguous仅candidate。
必须留下实际test/artifact，不以文字宣称完成。

### G104 R1公告有向路段映射
验收：端点/方向review图和unknown hours字段。
必须留下实际test/artifact，不以文字宣称完成。

### G105 F1火灾事实假设分离
验收：日期街道已核验；精确坐标/cordon需source或assumption。
必须留下实际test/artifact，不以文字宣称完成。

### G106 锁数据评估边界
验收：真实观测最多两轮检查、split/source manifests、missing-data report。
必须留下实际test/artifact，不以文字宣称完成。

## 执行loop

L1完整实现；失败进入L2至多3次；Qwen System-One用L3、数据用L0，评估用L4。保护原始tests与independent oracle。

## 退出命令（若未建立命令，在WP0/当前包实现真实target，不能echo成功）

```bash
make citypack-fetch
make citypack-build
make test-data
make case-review
```

产物必须包含 `evidence/wp1/citypack_audit.json`，记录commands/exit codes/artifact sha256/mode/scope。同步execution/goals.json、STATE.md。

## 自审必须问

是否实际调用了本包要求的外部/仿真能力？哪些仍是mock？哪些data只是current snapshot？有没有修改baseline/demand或label导致消融不公平？有没有新增非v1平台工程？

完成后返回实际交付/失败签名/可继续的下一WP，不重新询问已确定的城市/是否Web/是否本地。


<!-- SOURCE FILE: prompts/03_WP2.md -->

# WP2 · Road & Fire确定性GIS影响引擎完成

你负责交付这个完整工作包，不是生成下一份计划。先遵守根AGENTS与总prompt。

## 只加载这些详细文档

- docs/03_CONTRACTS.md
- docs/06_ROAD_FIRE_SUMO.md
- docs/08_TESTING.md

前置：WP0。允许外部blockers记录后并行不依赖工作，但对应release gate不可以PASS。

## 本批必须一起完成的goals

### G201 时间与车种限制编译器
验收：半开时间窗、未知edge拒绝、direction/class准确。
必须留下实际test/artifact，不以文字宣称完成。

### G202 独立可达性与路由比较
验收：turn-aware shortest paths、unreachable不为0。
必须留下实际test/artifact，不以文字宣称完成。

### G203 火灾外部限制输入
验收：点/区/道路→需确认restrictions，不生成火灾physics。
必须留下实际test/artifact，不以文字宣称完成。

### G204 设施与公交影响facts
验收：入口/route match分级、必查设施不被topK裁掉。
必须留下实际test/artifact，不以文字宣称完成。

### G205 边界与不完整数据处理
验收：扩大network验证、缺失指标不假0。
必须留下实际test/artifact，不以文字宣称完成。

### G206 oracle和反例全覆盖
验收：单向/唯一桥/转弯/平面交叉/无事件/权限反例。
必须留下实际test/artifact，不以文字宣称完成。

## 执行loop

L1完整实现；失败进入L2至多3次；Qwen System-One用L3、数据用L0，评估用L4。保护原始tests与independent oracle。

## 退出命令（若未建立命令，在WP0/当前包实现真实target，不能echo成功）

```bash
make test-network
make test-scenarios
make demo-road-fire
```

产物必须包含 `evidence/wp2/network_comparison.json`，记录commands/exit codes/artifact sha256/mode/scope。同步execution/goals.json、STATE.md。

## 自审必须问

是否实际调用了本包要求的外部/仿真能力？哪些仍是mock？哪些data只是current snapshot？有没有修改baseline/demand或label导致消融不公平？有没有新增非v1平台工程？

完成后返回实际交付/失败签名/可继续的下一WP，不重新询问已确定的城市/是否Web/是否本地。


<!-- SOURCE FILE: prompts/04_WP3.md -->

# WP3 · typed KG + 固定PPR + 真Qwen-System-One-PPR完成

你负责交付这个完整工作包，不是生成下一份计划。先遵守根AGENTS与总prompt。

## 只加载这些详细文档

- docs/04_KG_PPR.md
- docs/05_QWEN_SYSTEM_ONE.md
- docs/09_VALIDATION_ABLATION.md

前置：WP0, WP2。允许外部blockers记录后并行不依赖工作，但对应release gate不可以PASS。

## 本批必须一起完成的goals

### G301 真实typed temporal KG投影
验收：跨道路/公交/设施、provenance、方向和窗口审计。
必须留下实际test/artifact，不以文字宣称完成。

### G302 CSR PPR及独立oracle
验收：mass/residual/dangling/alpha，dense+NetworkX一致。
必须留下实际test/artifact，不以文字宣称完成。

### G303 paired delta可比较
验收：相同U/s/alpha/policy hashes，no-op=0。
必须留下实际test/artifact，不以文字宣称完成。

### G304 真实Qwen System-One协议与pipeline
验收：Score批量→合法policy→真实图PPR，缓存/本地endpoint/model revision/calibration/性能记录。
必须留下实际test/artifact，不以文字宣称完成。

### G305 解释路径和类型内显示
验收：路径引用真实edge，attention不伪装risk。
必须留下实际test/artifact，不以文字宣称完成。

### G306 防装饰消融钩子
验收：neutral/permute/no-PPR modes及单relation取消反例。
必须留下实际test/artifact，不以文字宣称完成。

## 执行loop

L1完整实现；失败进入L2至多3次；本地Qwen System-One用L3、数据用L0，评估用L4。保护原始tests与independent oracle。

## 退出命令（若未建立命令，在WP0/当前包实现真实target，不能echo成功）

```bash
make test-graph
make test-ppr
make test-systemone-contract
make test-systemone-local
make demo-ranking
```

产物必须包含 `evidence/wp3/ranking_integration.json`，记录commands/exit codes/artifact sha256/mode/scope。同步execution/goals.json、STATE.md。

## 自审必须问

是否实际调用了本包要求的本地Qwen模型/仿真能力？哪些仍是mock？哪些data只是current snapshot？有没有修改baseline/demand或label导致消融不公平？有没有新增非v1平台工程？

完成后返回实际交付/失败签名/可继续的下一WP，不重新询问已确定的城市/是否Web/是否本地。


<!-- SOURCE FILE: prompts/05_WP4.md -->

# WP4 · SUMO真正联调与paired仿真结果完成

你负责交付这个完整工作包，不是生成下一份计划。先遵守根AGENTS与总prompt。

## 只加载这些详细文档

- docs/06_ROAD_FIRE_SUMO.md
- docs/08_TESTING.md

前置：WP1, WP2。允许外部blockers记录后并行不依赖工作，但对应release gate不可以PASS。

## 本批必须一起完成的goals

### G401 真实binary安装和adapter
验收：版本锁、命令数组、logs、资源限额。
必须留下实际test/artifact，不以文字宣称完成。

### G402 network/demand映射
验收：有向edge到SUMO映射，same demand/seed，synthetic标签。
必须留下实际test/artifact，不以文字宣称完成。

### G403 hard closure/class运行
验收：禁止soft误用，多rerouter loop反例。
必须留下实际test/artifact，不以文字宣称完成。

### G404 before/after metrics
验收：arrived/unfinished/teleported完整分母，real输出。
必须留下实际test/artifact，不以文字宣称完成。

### G405 取消和失败隔离
验收：kill子进程、atomic产物、坏route不吞掉。
必须留下实际test/artifact，不以文字宣称完成。

### G406 Helsinki代表场景可跑
验收：bounded network和simulation coverage，未校准明确。
必须留下实际test/artifact，不以文字宣称完成。

## 执行loop

L1完整实现；失败进入L2至多3次；Qwen System-One用L3、数据用L0，评估用L4。保护原始tests与independent oracle。

## 退出命令（若未建立命令，在WP0/当前包实现真实target，不能echo成功）

```bash
make test-sumo
make demo-sumo-pair
make test-cancel
```

产物必须包含 `evidence/wp4/sumo_pair.json`，记录commands/exit codes/artifact sha256/mode/scope。同步execution/goals.json、STATE.md。

## 自审必须问

是否实际调用了本包要求的外部/仿真能力？哪些仍是mock？哪些data只是current snapshot？有没有修改baseline/demand或label导致消融不公平？有没有新增非v1平台工程？

完成后返回实际交付/失败签名/可继续的下一WP，不重新询问已确定的城市/是否Web/是否本地。


<!-- SOURCE FILE: prompts/06_WP5.md -->

# WP5 · 可嵌入Web GIS成品闭环

你负责交付这个完整工作包，不是生成下一份计划。先遵守根AGENTS与总prompt。

## 只加载这些详细文档

- docs/03_CONTRACTS.md
- docs/07_WEB_SECURITY.md

前置：WP0, WP2, WP3。允许外部blockers记录后并行不依赖工作，但对应release gate不可以PASS。

## 本批必须一起完成的goals

### G501 同一Web Component两宿主
验收：MapLibre+vanilla，真正同build artifact，dispose不泄漏。
必须留下实际test/artifact，不以文字宣称完成。

### G502 地图→scenario→运行
验收：道路/火灾输入、窗口/车种/assumption明确。
必须留下实际test/artifact，不以文字宣称完成。

### G503 进度取消失败体验
验收：API真实job，不虚拟输出，不吞Qwen System-One错误。
必须留下实际test/artifact，不以文字宣称完成。

### G504 事实/attention/证据联动
验收：before/after同标度，必查设施、why paths、模型状态。
必须留下实际test/artifact，不以文字宣称完成。

### G505 导出与重放入口
验收：结果ZIP含完整manifest/metrics/sources，不含key。
必须留下实际test/artifact，不以文字宣称完成。

### G506 local安全/offline
验收：same origin/token、恶意输入拒绝、offline零出网。
必须留下实际test/artifact，不以文字宣称完成。

## 执行loop

L1完整实现；失败进入L2至多3次；Qwen System-One用L3、数据用L0，评估用L4。保护原始tests与independent oracle。

## 退出命令（若未建立命令，在WP0/当前包实现真实target，不能echo成功）

```bash
make build-web
make test-web
make test-browser
make demo-local
```

产物必须包含 `evidence/wp5/browser_e2e.json`，记录commands/exit codes/artifact sha256/mode/scope。同步execution/goals.json、STATE.md。

## 自审必须问

是否实际调用了本包要求的外部/仿真能力？哪些仍是mock？哪些data只是current snapshot？有没有修改baseline/demand或label导致消融不公平？有没有新增非v1平台工程？

完成后返回实际交付/失败签名/可继续的下一WP，不重新询问已确定的城市/是否Web/是否本地。


<!-- SOURCE FILE: prompts/07_WP6.md -->

# WP6 · 成果验证、完整消融与性能成本报告

你负责交付这个完整工作包，不是生成下一份计划。先遵守根AGENTS与总prompt。

## 只加载这些详细文档

- docs/08_TESTING.md
- docs/09_VALIDATION_ABLATION.md
- docs/02_DATA_CASES.md

前置：WP1, WP3, WP4, WP5。允许外部blockers记录后并行不依赖工作，但对应release gate不可以PASS。

## 本批必须一起完成的goals

### G601 冻结48情景与独立labels
验收：按母题/走廊split，模型无heldout访问。
必须留下实际test/artifact，不以文字宣称完成。

### G602 公平运行A0–A5
验收：physical cache共享，real local Qwen System-One response冻结，负对照完整。
必须留下实际test/artifact，不以文字宣称完成。

### G603 R1源事实复现审计
验收：边界/方向/时间精度与公告对照，非数值准确性。
必须留下实际test/artifact，不以文字宣称完成。

### G604 F1真实地点情景审计
验收：incident事实与假设分开，不冒称实际管制/响应。
必须留下实际test/artifact，不以文字宣称完成。

### G605 如有观测则独立数值验证
验收：取得才评估，否则NOT_VALIDATED，不停工空转。
必须留下实际test/artifact，不以文字宣称完成。

### G606 成本性能与负结果
验收：raw metrics/置信区间适用性/预算/RSS/latency；无增益诚实报告。
必须留下实际test/artifact，不以文字宣称完成。

## 执行loop

L1完整实现；失败进入L2至多3次；Qwen System-One用L3、数据用L0，评估用L4。保护原始tests与independent oracle。

## 退出命令（若未建立命令，在WP0/当前包实现真实target，不能echo成功）

```bash
make test-outcomes
make ablate
make benchmark
make report
```

产物必须包含 `evidence/wp6/ablation_report.json`，记录commands/exit codes/artifact sha256/mode/scope。同步execution/goals.json、STATE.md。

## 自审必须问

是否实际调用了本包要求的外部/仿真能力？哪些仍是mock？哪些data只是current snapshot？有没有修改baseline/demand或label导致消融不公平？有没有新增非v1平台工程？

完成后返回实际交付/失败签名/可继续的下一WP，不重新询问已确定的城市/是否Web/是否本地。


<!-- SOURCE FILE: prompts/08_WP7.md -->

# WP7 · 干净环境发布验收与完整工程交付

你负责交付这个完整工作包，不是生成下一份计划。先遵守根AGENTS与总prompt。

## 只加载这些详细文档

- docs/11_RELEASE.md
- docs/07_WEB_SECURITY.md

前置：WP6。允许外部blockers记录后并行不依赖工作，但对应release gate不可以PASS。

## 本批必须一起完成的goals

### G701 clean checkout重建
验收：locks/container、文档命令实际可跑。
必须留下实际test/artifact，不以文字宣称完成。

### G702 全部must gates
验收：contracts/network/KG/PPR/Qwen System-One/SUMO/web/realcity/ablation/security/reproduce。
必须留下实际test/artifact，不以文字宣称完成。

### G703 独立审查与mutation
验收：关键错误必须被tests挡住，reviewer不伪称人类专家。
必须留下实际test/artifact，不以文字宣称完成。

### G704 许可隐私与数据分发
验收：source attribution/SBOM/no secret/数据包许可单列。
必须留下实际test/artifact，不以文字宣称完成。

### G705 完成用户文档和演示
验收：local安装、真实模式切换、限制/negative findings可见。
必须留下实际test/artifact，不以文字宣称完成。

### G706 准确声明完成与缺口
验收：工程complete与measured validation分开，发布/推送需明确授权。
必须留下实际test/artifact，不以文字宣称完成。

## 执行loop

L1完整实现；失败进入L2至多3次；Qwen System-One用L3、数据用L0，评估用L4。保护原始tests与independent oracle。

## 退出命令（若未建立命令，在WP0/当前包实现真实target，不能echo成功）

```bash
make clean-checkout-test
make security-check
make release-check
```

产物必须包含 `evidence/wp7/release_review.json`，记录commands/exit codes/artifact sha256/mode/scope。同步execution/goals.json、STATE.md。

## 自审必须问

是否实际调用了本包要求的外部/仿真能力？哪些仍是mock？哪些data只是current snapshot？有没有修改baseline/demand或label导致消融不公平？有没有新增非v1平台工程？

完成后返回实际交付/失败签名/可继续的下一WP，不重新询问已确定的城市/是否Web/是否本地。


<!-- SOURCE FILE: prompts/09_RESUME.md -->

# RESUME

读取AGENTS.md和execution/STATE.md，再读上个WP产物摘要及git diff。复核最近一次test的实际exit code，选择下一个未完成且前置满足的完整WP。不要重读全MASTER_PLAN、重新选型或重建已通过模块。保留用户修改。blocked外部资源仅在条件已变化时重试；推进剩余独立goals。输出简短checkpoint并直接实现。


<!-- SOURCE FILE: prompts/10_REPAIR.md -->

# REPAIR

只处理给定失败签名。列出一个能被验证的原因假设，定位最小输入，先运行能复现的测试，再做最小正确修复，运行focused+相关回归。最多3轮不同假设；不得删除失败test、调整期望迎合错误输出、重写全部架构或持续重装依赖。三轮后生成独立repro和下一具体diagnostic，标记真实blocked，不虚报PASS。


<!-- SOURCE FILE: prompts/11_INDEPENDENT_REVIEW.md -->

# INDEPENDENT_REVIEW

作为独立代码审查角色，仅读scope/契约、diff、测试日志、产物hash及相应源证据。寻找方向/单位/时间/数据日期/label泄漏/实际Qwen System-One未入计算/soft closure/未到达消失/秘密泄露/假证据。用可复现反例支撑每个问题。不要重新实现整项目，不提出v2功能。对任何“真实预测验证”核查是否独立观测；对PPR分数是否被当风险提出阻塞。你不是人类消防专家，不声称专家认证。


<!-- SOURCE FILE: prompts/12_REAL_WORLD_VALIDATION.md -->

# REAL_WORLD_VALIDATION

执行docs/02与09，先取得并冻结真实bytes、查date覆盖，然后对照cases中source facts建立review map。不可将公告输入自身当独立outcome；不可用今天GTFS装历史；火灾case assumptions必须逐字段显示。最多两轮获取历史观测，找到则holdout验证，找不到写NOT_VALIDATED并完成source replay和what-if。每个score有分母、missing、data hash、allowed claim。不要重复网页搜索直到得到想要的结论。


<!-- SOURCE FILE: prompts/13_ABLATION.md -->

# ABLATION

冻结data/splits/physical facts，确认A0–A5唯一差异来自声明模块。先跑廉价oracle筛bug，再在相同情景执行A0/A1/A2/A3/A4/A5。A3用真实Qwen System-One政策记录，缓存复用，禁止按edge重复请求。只在dev调整有限参数；test不做prompt寻优。报告所有变体原始数据、成本/耗时/coverage与负结果。若Qwen System-One无效检查row归一化是否取消类型权重；正确取消应报告，不得注入噪声。


<!-- SOURCE FILE: prompts/14_RELEASE_REVIEW.md -->

# RELEASE_REVIEW

从clean checkout执行全部release命令。任何must test SKIP/MOCK/BLOCKED均不算PASS。核查真实本地Qwen System-One model/config/calibration manifest、Helsinki数据hash、SUMO日志、双宿主浏览器trace、消融raw metrics与安全检查。运行scripts/check_release.py，但不把结构检查当证据真实性证明。给出engineering complete及measured validation各自状态；不自动push或部署公网。


<!-- SOURCE FILE: prompts/15_SECURITY_AND_EGRESS.md -->

# SECURITY_AND_EGRESS

审核本地服务bind/session token/CORS、文件路径/ZIP/子进程/SSRF/XSS/日志redaction、取消和job隔离。离线测试拦截所有外部连接，含字体tiles和模型。Qwen System-One 默认仅连接部署者本地/内网 Reflex endpoint，不需要 BYOK；非loopback必须显式opt-in并记录egress scope。不得泄露原始graph或敏感设施信息。远程廉价LLM仍为BYOK且默认关闭。机构SSO/多用户归部署者，不因此省略软件安全底线，也不要趁机实现用户管理平台。


<!-- SOURCE FILE: prompts/16_SEMANTIC_VS_PHYSICAL.md -->

# SEMANTIC_VS_PHYSICAL

追踪一个火灾或封路情景的每个结果数字。从输入数据→路由/SUMO→ResultBundle→UI逐项核验。PPR只能是attention；Qwen System-One只能soft relevance。找出被误称风险/真实response的字段、NA填0、未到达删除、任意radius及用NEAR断言served-by。每个问题写测试并修复，不用LLM文本解释掩盖。


<!-- SOURCE FILE: prompts/17_ONTOLOGY_AND_BENCHMARK.md -->

# Prompt · Operational Ontology + Competitive Benchmark Integration

读取 docs/14_OPERATIONAL_ONTOLOGY.md 和 docs/15_COMPETITIVE_BENCHMARK.md，并将其视为 v1 的规范性要求，不是未来愿望。

目标：在不扩大成通用 ontology platform 的前提下，把现有 Road & Fire GIS v1 从“KG + 算法”升级为 object/link/action/function 驱动的 operational ontology。

一次完成以下纵向闭环：

1. 建立 versioned ontology manifest，注册 v1 ObjectType / LinkType / Interface / ActionType / Function signatures；
2. 从 manifest 生成或一致性校验 Pydantic / JSON Schema / TS types，不维护分叉 schema；
3. authoritative city snapshot immutable；Scenario 通过 overlay + typed Actions 修改有效状态；
4. 实现 ActionRecord、precondition validation、atomic scenario workspace commit、replay hash；
5. LLM/System-One 不允许直接 CRUD graph；LLM只产生 action draft，Qwen只产生 soft semantic policy；
6. Operational Ontology 通过 ProjectionSpec 生成 PPR graph，审计/Run/Evidence 等对象默认不进入PPR；
7. Web Object View 展示 identity/state/links/facts/attention/evidence/actions/history；
8. 增加 T-ONTOLOGY 与 mutation tests；
9. 建立 comparison/feature_matrix.csv 和 benchmark manifest；只填有证据的 yes/no/partial/unknown；
10. 运行现有 A0–A5、工程性能 benchmark，并对至少一个可运行邻居项目写 reproduction notes；不做不公平总分排名。

硬边界：不复制 Palantir 专有代码/API，不依赖 Palantir，不做通用 ontology builder，不引入 Neo4j/RDF server作为v1硬依赖，不修改authoritative city data，不把PPR叫风险/因果，不把竞争项目 unknown 功能写成 no。

完成后更新 docs、contracts、work package evidence、release manifest；报告实际命令/exit code/artifact/hash。不要只写设计文档后宣布完成。


<!-- SOURCE FILE: comparison/README.md -->

# Comparison workspace

`feature_matrix_initial.csv` is a conservative seed matrix for Codex review, not a final published comparison. Every non-CiviFlux cell must be rechecked against a dated source or actual reproduction. `unknown` is not `no`. See `docs/15_COMPETITIVE_BENCHMARK.md`.


<!-- SOURCE FILE: sources/SOURCES.md -->

# Sources registry · human-readable mirror

## [S01] Helsinki City Run road notice

https://www.hel.fi/en/news/running-events-take-to-the-streets-of-helsinki-in-spring-and-early-summer

状态：WEB_VERIFIED；类别：official_city。

Planned road restrictions and some separately scoped pedestrian/cycle times; no measured traffic outcomes.

## [S02] Kalasatama fire incident reporting

https://yle.fi/a/74-20229203

状态：WEB_VERIFIED；类别：original_reporting。

Leonkatu apartment; incident notification at20:55; no road-perimeter data. Original reporting referring to accident report.

## [S03] HSL open data and licenses

https://www.hsl.fi/en/hsl/open-data

状态：WEB_VERIFIED；类别：official_operator。

GTFS latest and OSM extract links, forward schedule coverage; data licensing. Actual bytes not downloaded here.

## [S04] OSM copyright and license

https://www.openstreetmap.org/copyright

状态：WEB_VERIFIED；类别：official_standard。

ODbL/attribution. Does not grant unrestricted hosted tile use.

## [S05] MapLibre GL JS documentation

https://maplibre.org/maplibre-gl-js/docs/

状态：IMPLEMENTATION_REFERENCE_NOT_REVIEWED；类别：official_software。

Check current build API/versions in WP0; no promise of host-platform compatibility.

## [S06] GTFS schedule reference

https://gtfs.org/documentation/schedule/reference/

状态：WEB_VERIFIED；类别：official_standard。

GTFS service dates and times; implement >24:00 and exceptions carefully.

## [S07] HSL hfp-analytics README

https://github.com/HSLdevcom/hfp-analytics

状态：WEB_VERIFIED；类别：official_repository。

README describes an API that is not public; repository existence does not establish public historical HFP access.

## [S08] HRI Helsinki traffic volumes catalog

https://hri.fi/data/en_GB/dataset/liikennemaarat-helsingissa

状态：CATALOG_DISCOVERED_BYTES_UNVERIFIED；类别：official_catalog。

Potential observed traffic data. Date/station/format coverage has NOT been verified for either event.

## [S09] SUMO Rerouter

https://eclipse.dev/sumo/docs/Simulation/Rerouter.html

状态：WEB_VERIFIED；类别：official_software。

Soft vs hard closures; permissions; simultaneous rerouter mode8 loop warning.

## [S10] NetworkX PageRank reference

https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.link_analysis.pagerank_alg.pagerank.html

状态：WEB_VERIFIED；类别：official_software。

Alpha is link-following probability, dangling semantics and convergence behavior.

## [S11] SUMO about and licensing

https://eclipse.dev/sumo/about/

状态：WEB_VERIFIED；类别：official_software。

Free/open-source simulation suite, netconvert, routing, EPL2 license; check individual bundled components.

## [S12] Jev HTTP API reference (historical)

https://docs.typesafe.ai/api

状态：WEB_VERIFIED；类别：official_provider。

Historical Jev context only; NOT an UrbanImpact runtime dependency after Qwen System-One migration.

## [S13] Jev Quickstart (historical)

https://docs.typesafe.ai/introduction/quickstart

状态：WEB_VERIFIED；类别：official_provider。

Historical Jev context only; NOT an UrbanImpact runtime dependency after Qwen System-One migration.

## [S14] Jev model catalog and pricing (historical)

https://docs.typesafe.ai/models

状态：WEB_VERIFIED；类别：official_provider。

Historical Jev context only; NOT an UrbanImpact runtime dependency after Qwen System-One migration.

## [S15] Jev confidence (historical)

https://docs.typesafe.ai/confidence

状态：WEB_VERIFIED；类别：official_provider。

Historical Jev context only; NOT an UrbanImpact runtime dependency after Qwen System-One migration.

## [S16] Jev 1.13 jaggedness (historical)

https://docs.typesafe.ai/model-jaggedness/jev-1.13

状态：WEB_VERIFIED；类别：official_provider。

Historical Jev context only; NOT an UrbanImpact runtime dependency after Qwen System-One migration.

## [S17] Codex AGENTS.md guide

https://developers.openai.com/codex/guides/agents-md/

状态：WEB_VERIFIED；类别：official_software。

Project instructions, layered discovery; short root AGENTS and selective detailed docs.

## [S18] Port of Helsinki August22 marathon notice

https://www.portofhelsinki.fi/en/about-us/port-of-helsinki/whats-new/helsinki-marathon-affects-traffic-on-22-august/

状态：WEB_VERIFIED；类别：official_port。

Backup event timing notice; warns disruption not hard road closures; not core case.

## [S19] HSL HFP realtime documentation

https://digitransit.fi/en/developers/apis/5-realtime-api/vehicle-positions/high-frequency-positioning/

状态：WEB_VERIFIED；类别：official_operator。

Realtime data protocol; historical archive must be separately established.

## [S20] SUMO routes from observation points

https://eclipse.dev/sumo/docs/Demand/Routes_from_Observation_Points.html

状态：WEB_VERIFIED；类别：official_software。

Demand estimation from counts is not automatically calibrated/validated.

## [S21] Kalasatama incident date corroboration

https://yle.fi/a/74-20227939

状态：WEB_VERIFIED；类别：original_reporting。

Photo caption explicitly states Saturday May23 fire; corroborates date without inferring from relative weekdays.

## [S22] Reflex: local open System-One model on Qwen3.5

https://github.com/kshetrajna12/reflex

状态：WEB_VERIFIED；类别：open_source_project。

MIT; local /v1/systemone; Qwen3.5-4B default; typed Choice/Score/Noul. Current release path documents a 16 GB CUDA GPU; smaller WebGPU demo is not release-quality evidence. Workload-specific calibration/evaluation is still required.

## [S23] Qwen3.5-4B model

https://huggingface.co/Qwen/Qwen3.5-4B

状态：WEB_VERIFIED；类别：official_model_publisher。

Official Qwen model repository; Apache-2.0.

## [S24] Qwen3.5 4B System-One scorer research alternative

https://huggingface.co/pngwn/system-one-qwen3.5-4b-scorer

状态：WEB_VERIFIED；类别：community_model。

Single-pass typed scorer and calibration results; current model card license CC-BY-NC-4.0, therefore research/ablation only, not default distribution dependency.


<!-- SOURCE FILE: evidence/PACK_TEST_REPORT.md -->

# 本次实际执行的参考测试报告

生成时间：2026-09-23T13:49:48.289423+00:00。执行范围：**handoff 独立 reference checks**，不是未来 UrbanImpact 产品。

## 本次迁移结论

- hosted Jev / TypeSafe 注册、API key、token 计费已从 GIS v1 的必需依赖中移除。
- v1 System-One 改为 `QwenSystemOneBackend`；参考运行时为本地/私网 **Reflex + Qwen3.5-4B**。
- 当前 handoff 容器没有 Reflex/Qwen 服务，因此真实本地模型 gate 被正确标记为 `BLOCKED_ENVIRONMENT`，没有用 mock 冒充通过。
- DeepSeek / GPT-5.6 Luna 等廉价 LLM 仍是可选 `LanguageBackend`，不属于 v1 release 必需 gate。

## handoff-3 Operational Ontology 更新

- 新增 `docs/14_OPERATIONAL_ONTOLOGY.md`：Object/Link/Interface/Action/Function/Projection 规范；Palantir 仅作为公开架构思想参考，不成为依赖。
- 新增 `docs/15_COMPETITIVE_BENCHMARK.md`：EU Urban Flow、TWA、CReDo、TUM rescuePY、NYU/FDNY、SUMO_LLM_Agent、FireCom 的机构背景、功能差异和公平比较方法。
- 工程目标由 48 增为 **54**；新增 ontology/action/projection/object-view/competitor-benchmark/release-audit 六个硬验收目标。
- 新增 `ontology_manifest.schema.json` 与 `action_record.schema.json`；pack audit 会验证这些 JSON Schemas。
- 当前 reference tests 仍为 **66 passed**；它们验证 handoff 参考实现和协议，不代表产品 ontology/runtime 已开发完成。

## 已实际执行

| 命令 | 结果 | 证据 |
|---|---|---|
| `python -m pytest -q tests --junitxml=evidence/reference-junit.xml` | **66 passed**，exit 0 | `reference-pytest.txt` / `reference-junit.xml` |
| `python scripts/audit_pack.py` | **8 work packages / 54 goals / 39 sources，PASS** | `pack-audit.txt` |
| `python scripts/run_reference_demo.py` | 合成小图 routing + typed policy → transition → PPR，exit 0 | `reference_outcomes.json` / `reference-demo.txt` |
| `qwen_systemone_smoke.py` 指向未监听 loopback 端口 | **预期 BLOCKED_ENVIRONMENT，exit 2**；不会访问外部 AI | `qwen-systemone-smoke-blocked.txt` |
| `python scripts/check_release.py evidence/product_release.json` | **预期 exit 1**；产品 gates 尚未执行 | `product-release-gate.txt` |

## 参考成果，不是真实城市预测

固定 toy 路网 A→H 基线成本 **3 秒**；封 `bc` 后 **7 秒**；封唯一末端 `ch` 后为**不可达/null**。这些秒数只是自定义测试权重，不是 Helsinki 行程时间。

typed mock policy 改变后 PPR 向量 L1 差 **0.268018018018**，证明 policy 确实进入 transition/ranking 代码。该 policy 明确是测试 mock，不能证明 Qwen System-One 本身有效。

power iteration 与独立线性方程 oracle 最大绝对差约 **2.406e-13**；residual L1 约 **8.899e-13**。测试同时验证：同一节点全部出边统一缩放会被 row normalization 抵消，因此不能把“调用了模型”冒充成“模型改变了排名”。

## 当前没有完成

没有完整生产插件、真实 Helsinki citypack bytes、SUMO 实城 paired run、浏览器 E2E、真实 Qwen System-One graph integration、独立历史 traffic outcome 数值验证。

Reflex 当前文档的发布用 4B 路径面向 CUDA GPU；本 handoff 环境没有对应模型服务，因此 release gate 必须保持未完成。正式开发应在部署者本地或私网 GPU 主机跑真实 inference，保存 Reflex commit、Qwen revision、device/dtype、permutations、calibration hash 和 applied transition hash。

这是工程执行包的已测参考基线，不是全插件完成声明。
