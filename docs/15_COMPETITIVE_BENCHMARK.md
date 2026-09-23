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
