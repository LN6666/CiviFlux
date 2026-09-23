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
