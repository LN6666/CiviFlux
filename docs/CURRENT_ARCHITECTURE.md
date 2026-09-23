# 当前实现架构

CiviFlux 把物理事实、语义注意力和证据分开保存。用户确认的逻辑流程是 `Ontology → KG → Physical results → Semantic policy → PPR → Language explanation`。实现中以 `CityPack + Scenario → Routing / SUMO → scenario projection + semantic policy → PPR → ResultBundle` 完成物理结果与图政策的衔接；语言解释读取已冻结事实。用户修改先经过 typed Action 与不可变 overlay；UI 不直接修改 authoritative city 或 graph edges。

## 模块边界

| 模块 | 主要实现 | 责任 |
|---|---|---|
| Wire contracts | `core/urbanimpact/contracts.py` | Pydantic 数据验证、typed time/class/window、result bundle；未知字段拒绝 |
| Ontology | `ontology/manifest.yaml` | Object/Link/Interface/Action/Function/Evidence 注册和版本 |
| Workspace | `core/urbanimpact/actions.py` | immutable snapshot、SQLite transaction、Action preconditions/commit/replay |
| Network | `core/urbanimpact/network.py` | `[start,end)` restriction compiler、有向 edge-state Dijkstra、全设施事实、边界比较 |
| Projection | `core/urbanimpact/graph.py` | 从 ontology/source facts 构造有声明关系策略的 temporal graph |
| Ranking | `core/urbanimpact/ranking.py` | 确定性 PPR、paired comparison、语义权重与数值检查 |
| Use case | `core/urbanimpact/pipeline.py` | physical cache、计算阶段、provider 接入、ResultBundle 生成 |
| HTTP service | `api/app.py`, `api/services.py` | 同源 token、registered citypacks、Action API、有界单 worker jobs、取消、Object View/export |
| Data adapters | `adapters/osm/`, `adapters/gtfs/`, `core/urbanimpact/citypack/` | 明确出网获取、来源哈希、current citypack 和候选关联 |
| Native simulation | `adapters/sumo/` | pinned native conversion、shared demand/seed pair、hard closures、解析与资源限制 |
| Semantic provider | `adapters/system_one/` | SimpleJev typed classifier、远程 API；普通生成式 Qwen 仅可选比较，生产付费调用暂缓 |
| Web integration | `web/src/` | Web Component、LocalAPI、MapAdapter；MapLibre 与 NullMap 宿主复用组件 |

## 场景与审计

`Workspace` 保存 city snapshot 的 canonical bytes。读取会重新验证为新值，避免嵌套 mutable dict 旁路改变权威数据。`CreateScenario`、`AddRoadRestriction`、`CreateFireIncident`、`AttachImportedPerimeter`、`ChangeAnalysisPolicy` 等 Action 经参数签名和前置条件检查后提交。

Action records 记录 action identity、input/output refs、参数/provenance hashes 与状态。用户/LLM 都只能走同一验证路径；LLM draft 还需用户确认。assumed evidence 不能通过附件或普通编辑升级成 observed。未知/过期 overlay hash 要拒绝。

## 路由与 SUMO

路由以 incoming edge 为 state，避免 node-only shortest path 绕过转弯禁止。同车种 baseline/event 使用同一网络和权重，event 只应用显式时间限制。索引在一次 compare 内复用，每个 origin/stage 一次搜索覆盖全部设施；界面 top-K 不影响全设施检查。该全集只覆盖选定 origin、车种与时刻，不能扩展解释为全市所有起点的设施服务保证。

没有 facility entrance 返回 `unavailable`，断路返回 `unreachable`，真实起终点相同才是零距离/时间。emergency 车种不自动取得逆行或穿越禁行权限。公交 shape proximity 只生成 candidate association，不代表实测延误或取消。

SUMO adapter 将 directed IDs 映射为 native IDs，生成一次网络/route input，由 baseline/event 共用。重叠时间窗编译成单一 rerouter 的不重叠 interval；权限交集保证 closure 不意外打开原本禁止的车种。Mode 8 配合一个 rerouter 和 disabled teleport；独立 fixture 验证无备选路线时等待/未完成。

输出目录包括 replay inputs、native logs 和 hashes。success report 仅在两次 native 进程均成功且结果解析成功后原子写入。超时、输出限额、取消和错误日志产生 failure evidence，不产生成功文件。

## Projection 与语义政策

图是 ontology 的一个允许列表投影，审计/run/evidence 对象不自动进入排名。baseline/event 对比需同 node universe、seed、alpha 和 relation policy。物理 cache 与 ranking variant 分离，不为每个模型消融重新随机生成需求或改变 travel metrics。

投影前必须核对物理结果的城市快照、完整物理情景输入指纹、分析时刻、车种与生效限制。只改变 objective、ranking 或 scenario ID 的政策消融可共用物理结果；换种子、封路或其他物理输入则不能复用旧路径。这是防止陈旧 cache 污染派生 KG 的运行边界，不把物理结果改写为权威城市事实。

`baseline` / `event` 为物理路由导出的 operational projections；静态公交匹配保存在单独的 `dependency_evidence` projection。Object View 显示两种关系的明确标签，静态匹配不能解释成事件时刻仍可通行的公交路径。选择已完成 run 时，视图读取该 run 保存的 scenario/actions，并核对 snapshot/overlay/history hashes；后来编辑工作区不会改写旧运行的解释。

当前目标是通过远程 API 调用用户指定的 SimpleJev Qwen classifier，保留服务的 typed response 与 provenance；不在本地启动模型。生产付费 gate 为 `DEFERRED_USER`，公开 demo 单独标记。只发送批准的抽象关系定义与 objective，校验 schema、完整 key 集、有限值、服务分数语义与模型 provenance；城市图、坐标和物理输入留在部署者环境。

普通 DashScope/Model Studio `QwenAPIBackend` 保留为可选对照。它生成的 `[0,1]` relevance 不能冒充 SimpleJev typed classifier 输出，也不能满足该 System-One gate。SimpleJev 生产、SimpleJev demo、普通 qwen_api、replay、rules 和 mock_test 的 provenance 必须分开；classifier 分数也不能自动宣称已校准为现实正确率。模型价值由独立 hold-out/ablation 判断，协议成功与模型优于固定 PPR 是不同验收。

## API 与 Web

API 默认 loopback，同源检查、TrustedHost 和 Bearer session token 保护本地调用。它接受 schema-validated city JSON 和 typed Actions，不提供任意 URL proxy、文件路径读取或 shell command endpoint。服务以单 worker 执行有界队列；SQLite 写入在短事务内，不把长计算放进锁住的事务。

`MapAdapter` 的有限接口是 `setData`、`highlight`、`setPerimeter`、`fitExtent`、`onSelect`、可选 `drawPolygon` 和 `dispose`。组件不依赖 MapLibre 实例；普通 HTML 宿主使用 `NullMapAdapter`。浏览器只访问同源 API，不携带或调用模型 key/endpoint。unmount 必须释放订阅、地图对象和任务请求。

## 扩展与非目标

增加模型 provider 时实现 `score_relations` 边界并保留证据/预算语义；增加地图宿主时实现小型 `MapAdapter`。新增情景必须注册 typed objects/actions 并保留物理验证，而不是引入通用插件市场框架。

v1 的 KG 按 `analysis_time` 过滤时间有效性，由不可变 CityPack 与可重放的 Action overlay 派生；它不是持续更新的实时图。PPR 的排名证据和 SimpleJev 的语义政策随 ResultBundle 保存，语言模型只能提出待验证的 Action 草案；三者都不能直接修改权威对象或关系。只有可信来源的重新摄取可形成新版 CityPack，或已校验 Action 可形成新情景 overlay。若以后接入可信连续数据源，并出现明确的刷新时限、乱序/撤回更正需求及增量图计算负载，再设计带事件时间、来源版本、重放与快照隔离的动态 KG；该升级不属于 v1 的必要路径。

v1 不提供 CFD、烟热传播、火场半径推断、派车决策、撤离安全证明、机构身份/SSO、代运营 SaaS 或市政高可用设施。部署者负责网络、用户与备份治理；这不能被误写成代码已经提供多租户安全。
