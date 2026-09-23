# 8个大工作包 / 54 goals

每个WP一次推进完整能力；goals用来验收，不要求54轮对话。
本文件的工作包结构沿用原始工程包；模型运行路径以 [USER_DECISIONS.md](USER_DECISIONS.md) 为准：托管 Featherless SimpleJev API，禁止本地 Qwen，生产调用暂缓。实时进度以 [STATE.md](STATE.md) 和 `goals.json` 为准。

## WP0 一次打通工程骨架、契约、toy运行与Qwen System-One预检
前置：[]。Prompt：prompts/01_WP0.md

- **G001** 建立可运行monorepo与锁文件：Python API、TypeScript component构建，版本/许可可追溯，不只空目录
- **G002** 冻结Scenario/Result/KG契约：JSON Schema/Pydantic/TS一致性测试与无效输入拒绝
- **G003** 贯通toy纵向运行：scenario→route facts→graph→PPR→ResultBundle，从API可取实际数值
- **G004** 托管 SimpleJev 环境预检：检查官方 endpoint、指定 classifier、凭据、egress 与调用预算；未授权则精确 `DEFERRED_USER`，不下载或启动本地模型
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
- **G602** 公平运行A0–A5：physical cache共享，真实托管 SimpleJev 响应及 provenance 冻结，生产付费调用须先授权，负对照完整
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
