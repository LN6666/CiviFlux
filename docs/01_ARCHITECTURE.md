# 01 · 架构与实现取舍

本页保留原工程包的架构取舍；模型运行方式与当前实现请以 [用户决定](../execution/USER_DECISIONS.md)、[当前架构](CURRENT_ARCHITECTURE.md)和 [SimpleJev adapter](../adapters/system_one/README.md) 为准。下文涉及本地 Reflex/Qwen 的缓存 pin 或部署要求已被托管 API 决定覆盖。

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
