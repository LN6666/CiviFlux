# 54 项目标验收与接手清单

更新：2026-09-24。这是对现有产物和检查记录的逐项核对；本次只更新交接记录，没有新增运行、标签、代码或实验。

**当前计数：** PASS 38，PARTIAL 14，DEFERRED_USER 1，BLOCKED_EXTERNAL 1；合计 54。不是 54/54 完成。

PASS 只覆盖该行写明的验收范围；PARTIAL 表示已有实现/证据但仍有条款未验证；DEFERRED_USER 是用户推迟的付费工作；BLOCKED_EXTERNAL 是来源/独立观测不可得。原始验收文本保留在 [goals.json](goals.json)，每项目标另列 assessment、remaining_steps 和证据。

## 当前决定与范围

- 以 [USER_DECISIONS.md](USER_DECISIONS.md) 为准：只用远程 Featherless SimpleJev `Qwen3.8-27B-classifier`，禁止本地模型下载/部署；普通 Qwen chat 不能替代 classifier。旧文档中的 local/Reflex gate 已明确覆盖。
- 免费 demo 共 3 次请求，真实 typed policy 已用于 toy/Helsinki 图，物理事实不变。这是集成证据；生产 paid 调用、独立专家语义标签、校准、模型优越性仍未通过。不要再次消耗免费配额或自动开启 paid。
- Ontology 仅服务 Road & Fire v1 所需概念、Actions 和投影；不扩展通用城市平台、调度、安全判断或 CFD。PPR 只表示 attention。
- 207 项 Python 检查通过（包含 66 项原参考检查），6 项真实浏览器检查通过；两类检查不混称产品独立验证。native clean checkout/wheel 通过，Docker 和 image digest 未验收。
- Helsinki 仅当前快照 what-if：人工道路/入口核验、历史网络/feed、真实交通观测和真实火场边界仍缺。选择起点的不可达不等于全市设施隔离。

## 逐项目标

| ID | 目标 | 状态 | 已有证据与剩余步骤 |
|---|---|---|---|
| G001 | 建立可运行monorepo与锁文件 | PASS | Python API、TypeScript 组件、固定依赖及代码许可证已落地；native 安装和浏览器构建有实际证据。 [clean_checkout.json](../evidence/wp7/clean_checkout.json)、[browser_validation.json](../evidence/wp5/browser_validation.json) |
| G002 | 冻结Scenario/Result/KG契约 | PASS | 同源 Pydantic/JSON Schema/TS 生成校验及非法输入拒绝已执行。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[contracts_check.log](../evidence/wp7/contracts_check.log) |
| G003 | 贯通toy纵向运行 | PASS | 真实 API 获取 toy 路由数值、投影和收敛 PPR，浏览器调用同一后端。 [walking_skeleton.json](../evidence/wp0/walking_skeleton.json)、[browser_validation.json](../evidence/wp5/browser_validation.json) |
| G004 | 真实远程 SimpleJev（用户覆盖） System-One环境预检 | PARTIAL | 按用户决定改为远程 SimpleJev；免费 typed HTTP smoke 和图应用通过，未获得精确服务器/权重版本和校准。 **待补：**取得可验证的托管服务/权重版本或明确可接受的版本漂移策略。 独立专家语义标签与校准尚未完成；生产 paid 调用继续 DEFERRED_USER。 [simplejev_graph_integration.json](../evidence/wp3/simplejev_graph_integration.json)、[systemone_simplejev_demo_smoke.json](../evidence/wp3/systemone_simplejev_demo_smoke.json) |
| G005 | 测试与命令入口 | PASS | Make 命令和 CI 定义已建立，产品 test_suite 与原参考 tests/verification 分开。 [Makefile](../Makefile)、[ci.yml](../.github/workflows/ci.yml) |
| G006 | 记录状态和边界 | PASS | STATE、当前架构和严格 release manifest 明确部分验收，不使用假 PASS。 [STATE.md](../execution/STATE.md)、[CURRENT_ARCHITECTURE.md](../docs/CURRENT_ARCHITECTURE.md) |
| G007 | 冻结Operational Ontology manifest与代码绑定 | PASS | 唯一版本化 Road & Fire 注册表绑定生成契约；snapshot/derived、Action 和投影验证已执行。 [manifest.yaml](../ontology/manifest.yaml)、[contracts_check.log](../evidence/wp7/contracts_check.log) |
| G101 | 下载并冻结OSM/GTFS | PASS | 冻结真实 OSM/GTFS 字节、来源、日期、SHA256 和许可证。 [citypack_audit.json](../evidence/wp1/citypack_audit.json)、[README.md](../data/README.md) |
| G102 | 构建标准实体与路网映射 | PARTIAL | 稳定 ID、SUMO 有向转向及 lineage 已构建；设施仅邻近道路候选入口。 **待补：**独立核验设施入口及其道路连接；复杂条件通行/转向缺口不得当作已验证。 [citypack_audit.json](../evidence/wp1/citypack_audit.json)、[missing_data_report.json](../evidence/wp1/missing_data_report.json) |
| G103 | 核验公交feed覆盖和shape匹配 | PASS | calendar/exception/>24h 已检查，历史日期不覆盖明确，shape 对齐保留 candidate。 [citypack_audit.json](../evidence/wp1/citypack_audit.json)、[test_ingest.py](../test_suite/data/test_ingest.py) |
| G104 | R1公告有向路段映射 | PARTIAL | 端点/方向候选、review 图和未知时间字段已保存；人工通过数为 0。 **待补：**人工确认公告至有向路段的边界/方向；未知时间和豁免只能由来源补足，不得推断。 [case_review.json](../evidence/wp1/case_review.json)、[directed_road_review.html](../evidence/wp1/directed_road_review.html) |
| G105 | F1火灾事实假设分离 | PASS | 真实日期/街道与假设道路、时间、车种分开；建筑坐标与实际 cordon 保持未知。 [case_review.json](../evidence/wp1/case_review.json)、[fire_scenario.json](../evidence/wp1/fire_scenario.json) |
| G106 | 锁数据评估边界 | PASS | 按两次外部失败停止规则记录观测缺口，split/source/missing-data 已保存。 [missing_data_report.json](../evidence/wp1/missing_data_report.json)、[evaluation_split_manifest.json](../evidence/wp1/evaluation_split_manifest.json) |
| G201 | 时间与车种限制编译器 | PASS | 半开时间、方向、车种、未知边拒绝均有产品反例检查。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[test_network.py](../test_suite/unit/test_network.py) |
| G202 | 独立可达性与路由比较 | PASS | 边状态 turn-aware 路由与独立枚举 oracle 一致；不可达时间为 null。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[ablation_report.json](../evidence/wp6/ablation_report.json) |
| G203 | 火灾外部限制输入 | PASS | 用户明确 polygon/道路及假设确认后创建火灾外部限制；缺范围拒绝，不生成物理火场。 [browser_validation.json](../evidence/wp5/browser_validation.json)、[workflow.spec.ts](../web/tests/workflow.spec.ts) |
| G204 | 设施与公交影响facts | PASS | 设施入口状态和公交关联分级，全部声明 OD 均检查，未被排名 topK 裁剪。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[ablation_report.json](../evidence/wp6/ablation_report.json) |
| G205 | 边界与不完整数据处理 | PARTIAL | 缺失指标保持未知且合成扩大裁剪反例通过；真实 Helsinki 边界稳定性未验证。 **待补：**在扩大真实路网范围后对相同 origin/OD/限制复核结果稳定性；目前只可报告选择起点的局部结果。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[citypack_audit.json](../evidence/wp1/citypack_audit.json) |
| G206 | oracle和反例全覆盖 | PASS | 单向/桥/转向/平面交叉/no-op/车种反例和独立枚举 oracle 已执行。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[ablation_report.json](../evidence/wp6/ablation_report.json) |
| G207 | Road/Fire全部通过typed Actions形成Scenario overlay | PASS | Road/Fire 经 typed Actions 事务提交、记录、重放；失败不部分提交且 baseline 不变。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[ontology_review.md](../evidence/wp0/ontology_review.md) |
| G301 | 真实typed temporal KG投影 | PASS | 版本化 typed temporal 投影具来源、方向和有效窗；公交静态依赖与 operational 图分开。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[ontology_review.md](../evidence/wp0/ontology_review.md) |
| G302 | CSR PPR及独立oracle | PASS | CSR PPR 与 dense/NetworkX 独立数值 oracle 比较，mass/residual/dangling/alpha 检查通过。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[test_graph_ranking.py](../test_suite/unit/test_graph_ranking.py) |
| G303 | paired delta可比较 | PASS | 比较上下文、node universe/seed/policy/图哈希均校验，no-op delta 为 0。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[ontology_review.md](../evidence/wp0/ontology_review.md) |
| G304 | 真实远程 SimpleJev（用户覆盖） System-One协议与PPR pipeline | PARTIAL | 3 次免费 SimpleJev 请求取得真实 typed policy，并在 toy/Helsinki 图应用且物理事实不变；仅集成证据。 **待补：**生产 endpoint 真实验证须待用户另行启用 paid 配额。 托管服务器/权重版本未报告；专家语义标签、校准与泛化验证未完成。 [simplejev_graph_integration.json](../evidence/wp3/simplejev_graph_integration.json)、[systemone_simplejev_relations_policy.json](../evidence/wp3/systemone_simplejev_relations_policy.json) |
| G305 | 解释路径和类型内显示 | PASS | witness 引用实际图边且搜索有界；UI 按类型显示 attention，不冒充风险。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[ontology_review.md](../evidence/wp0/ontology_review.md) |
| G306 | 防装饰消融钩子 | PARTIAL | neutral/no-PPR 分支及单一 relation 权重抵消检查存在；未执行真实模型权重 permutation 负对照。 **待补：**在真实冻结 policy 可用且对应实验获准后补 permutation 对照；不能把 A5 neutral 当作完整模型负对照。 [ablation_report.json](../evidence/wp6/ablation_report.json)、[test_graph_ranking.py](../test_suite/unit/test_graph_ranking.py) |
| G307 | Ontology ProjectionSpec生成scenario graph | PASS | 显式 ProjectionSpec 包含时间/空间范围/无隐含 hop 截断；audit/run/evidence 默认不进 PPR 并验证 hash。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[ontology_review.md](../evidence/wp0/ontology_review.md) |
| G401 | 真实binary安装和adapter | PASS | 真实 SUMO 1.27.1 固定依赖，命令数组、日志和时间/车辆/输出预算已检查。 [validation.json](../evidence/wp4/validation.json)、[uv.lock](../uv.lock) |
| G402 | network/demand映射 | PASS | 有向 edge 映射、相同 seed/demand 和 synthetic 声明随 paired 运行记录。 [validation.json](../evidence/wp4/validation.json)、[sumo_pair.json](../evidence/wp4/sumo_pair.json) |
| G403 | hard closure/class运行 | PARTIAL | 真实 hard closure、车种例外和同时封闭通过；尚无独立多 rerouter 循环反例的明确验收证据。 **待补：**核实或补充多个 rerouter 诱发循环的专门反例证据；不能仅由同时封闭测试推定已覆盖。 [validation.json](../evidence/wp4/validation.json)、[test_sumo.py](../test_suite/sumo/test_sumo.py) |
| G404 | before/after metrics | PASS | 真实输出包含 arrived/unfinished/pending/teleported/rejected 及到达均值分母。 [validation.json](../evidence/wp4/validation.json)、[sumo_pair.json](../evidence/wp4/sumo_pair.json) |
| G405 | 取消和失败隔离 | PASS | 真实进程树取消、输出限额、失败隔离、坏 route 不发布成功产物已有检查。 [validation.json](../evidence/wp4/validation.json)、[final_python_junit.xml](../evidence/wp7/final_python_junit.xml) |
| G406 | Helsinki代表场景可跑 | PASS | Helsinki 有界代表走廊真实 SUMO pair 已运行，覆盖和未校准 synthetic demand 明示。 [helsinki_sumo_pair.json](../evidence/wp4/helsinki_sumo_pair.json)、[validation.json](../evidence/wp4/validation.json) |
| G501 | 同一Web Component两宿主 | PARTIAL | 同一构建组件在 MapLibre/vanilla 两宿主真实运行；dispose 实现存在，缺反复 mount/unmount 泄漏验收。 **待补：**补重复挂载/卸载后的订阅、定时器、网络请求和地图资源释放检查。 [browser_validation.json](../evidence/wp5/browser_validation.json)、[panel.ts](../web/src/panel.ts) |
| G502 | 地图→scenario→运行 | PASS | 地图选择道路和导入显式火灾 polygon 均调用真实 Actions；时间/车种/assumption 确认可见。 [browser_validation.json](../evidence/wp5/browser_validation.json)、[workflow.spec.ts](../web/tests/workflow.spec.ts) |
| G503 | 进度取消失败体验 | PARTIAL | 真实 job 进度、失败和模型不可用显示已跑；API 取消持久化通过，浏览器取消流程未有专门 E2E。 **待补：**在运行中的真实 browser job 点击 Cancel，验证终态与无完成结果；保留已有 API/native 取消证据。 [browser_validation.json](../evidence/wp5/browser_validation.json)、[final_python_junit.xml](../evidence/wp7/final_python_junit.xml) |
| G504 | 事实/attention/证据联动 | PASS | before/after 原始同尺度数值、完整设施 facts、witness 和 provider 状态可关联查看。 [browser_validation.json](../evidence/wp5/browser_validation.json)、[panel.ts](../web/src/panel.ts) |
| G505 | 导出与重放入口 | PASS | 实际下载 ZIP 包含 scenario/actions/ontology/result/manifest，token 排除和 Action 重放均已验证。 [browser_validation.json](../evidence/wp5/browser_validation.json)、[final_python_junit.xml](../evidence/wp7/final_python_junit.xml) |
| G506 | local安全/offline | PASS | host/origin/token、路径拒绝、job 隔离和浏览器零外部请求已有检查；首次依赖下载另行标注。 [browser_validation.json](../evidence/wp5/browser_validation.json)、[final_python_junit.xml](../evidence/wp7/final_python_junit.xml) |
| G507 | Object-centric Web View与Action UI | PASS | 对象 identity/state/links/facts/attention/evidence/actions/history 可读；用户经 Action，不直接编辑图。 [browser_validation.json](../evidence/wp5/browser_validation.json)、[ontology_review.md](../evidence/wp0/ontology_review.md) |
| G601 | 冻结48情景与独立labels | PASS | 48 个合成场景/12 母题分组冻结，独立枚举生成机器 labels，输入白名单阻止 heldout/标签流入模型。 [manifest.json](../experiments/frozen/manifest.json)、[ablation_report.json](../evidence/wp6/ablation_report.json) |
| G602 | 公平运行A0–A5 | DEFERRED_USER | A0/A1/A2/A5 共 192 行共享 48 套物理事实；A3/A4 共 96 行未跑；免费图 smoke 不能替代完整消融。 **待补：**待生产调用获用户配额授权且独立模型评估设计冻结后执行 A3/A4 及完整负对照；保持相同 physical cache。 [ablation_report.json](../evidence/wp6/ablation_report.json)、[final_gate.json](../evidence/wp6/final_gate.json) |
| G603 | R1源事实复现审计 | PARTIAL | R1 来源和机器候选映射审计已保存；human_accepted=0，source replay 未验证，时间未知保持未知。 **待补：**独立人工逐条确认道路边界/方向并记录 reviewer；来源缺失的时段/豁免保留 unknown。 [case_review.json](../evidence/wp1/case_review.json)、[directed_road_review.html](../evidence/wp1/directed_road_review.html) |
| G604 | F1真实地点情景审计 | PASS | 真实 Leonkatu 地点情景已运行，实际火场、管制和响应没有被冒称复原。 [case_review.json](../evidence/wp1/case_review.json)、[helsinki_fire_product.json](../evidence/wp2/helsinki_fire_product.json) |
| G605 | 如有观测则独立数值验证 | BLOCKED_EXTERNAL | 未获得合格独立历史交通观测；数值验证明确 NOT_VALIDATED，两次外部失败后停止。 **待补：**取得事件日期/地点/单位/时间覆盖匹配的独立观测后才能验证数值预测；当前不为该缺口继续空转。 [missing_data_report.json](../evidence/wp1/missing_data_report.json)、[report.json](../evidence/wp6/report.json) |
| G606 | 成本性能与负结果 | PASS | raw metrics/latency/RSS/预算和分组描述区间已保存，明确非置信区间/非端到端性能，无模型增益主张。 [ablation_report.json](../evidence/wp6/ablation_report.json)、[benchmark.json](../evidence/wp6/benchmark.json) |
| G607 | 竞争功能矩阵与公平benchmark/reproduction | PASS | 152 格 source-backed matrix、内部 200k-edge benchmark、固定外部 OSS 真 smoke 与限制均保存，不作异任务总分。 [feature_matrix.csv](../comparison/feature_matrix.csv)、[SUMO_LLM_Agent.md](../comparison/reproduction_notes/SUMO_LLM_Agent.md) |
| G701 | clean checkout重建 | PARTIAL | 干净 committed HEAD 的 native 固定依赖、toy 和安装 wheel 通过；Docker 尚不可用且镜像未固定 digest。 **待补：**在可用 Docker 环境构建并执行容器 smoke，固定解析后的 base/image digest；不得将 native PASS 扩为容器 PASS。 [clean_checkout.json](../evidence/wp7/clean_checkout.json)、[clean_checkout_offline.json](../evidence/wp7/clean_checkout_offline.json) |
| G702 | 全部must gates | PARTIAL | contracts/network/graph/PPR/SUMO/web/security 有实际通过；全部 must gates 尚未满足。 **待补：**处理 production SimpleJev/完整消融、人工真实城市映射及容器复现缺口；strict release-check 当前应继续非零。 [current_product_release.json](../evidence/current_product_release.json)、[release_check.log](../evidence/wp7/release_check.log) |
| G703 | 独立审查与mutation | PASS | 独立子代理审查保留原反例，typed/context/hash/事务/witness/Object View 修复后回归通过；不是人类专家审查。 [ontology_review.md](../evidence/wp0/ontology_review.md)、[final_python_junit.xml](../evidence/wp7/final_python_junit.xml) |
| G704 | 许可隐私与数据分发 | PARTIAL | 许可证/NOTICE/来源许可、数据分发边界和发布文件秘密扫描完成；未发现机器可读 SBOM 产物。 **待补：**为固定 Python/JS/native 依赖生成并审查 SBOM 与第三方许可证清单；锁文件本身不等于 SBOM。 [LICENSE](../LICENSE)、[NOTICE](../NOTICE) |
| G705 | 完成用户文档和演示 | PASS | 当前 README/runbook/architecture 及截图覆盖本地安装、模式、证据和负结果；旧手交文档以用户决定和当前文档为准。 [README.md](../README.md)、[CURRENT_RUNBOOK.md](../docs/CURRENT_RUNBOOK.md) |
| G706 | 准确声明完成与缺口 | PASS | 工程部分验收与历史观测声明分开；记录 paid 推迟和已授权 GitHub 发布，不宣称 v1 全部完成。 [STATE.md](../execution/STATE.md)、[USER_DECISIONS.md](../execution/USER_DECISIONS.md) |
| G707 | Ontology/竞争比较发布审计 | PARTIAL | ontology/action/replay/projection 与外部比较证据齐全，NOTICE 无从属暗示；完整 release artifacts 仍缺容器/SBOM及未过 gates。 **待补：**完成 G701/G702/G704 缺口后再签定完整 v1 发布包；目前交付只能标明部分验收。 [ontology_review.md](../evidence/wp0/ontology_review.md)、[feature_matrix.csv](../comparison/feature_matrix.csv) |

## 接手顺序

1. 先读本清单与用户决定，再查看 strict [release manifest](../evidence/current_product_release.json)。发布源码已获用户授权，不代表全部 v1 gate 通过。
2. 可独立补齐：组件反复挂载释放检查、浏览器取消 E2E、多 rerouter 循环专门反例、SBOM；在 Docker 可用环境完成容器构建和 digest 复现。不要因此扩展 ontology 或产品范围。
3. 真实城市验证需人工确认公告边界/方向和设施入口，并检查扩大 ROI 的稳定性。历史数值验证必须取得合格观测；无数据时维持 NOT_VALIDATED。
4. 生产模型工作保持 DEFERRED_USER；用户明确启用配额后才做真实 A3/A4、冻结 policy/负对照和独立语义评估。专家标签与合成路径 oracle 是不同证据，不可互换。
5. 复用未变输入/源码的证据；只运行受后续变更影响的检查。更改 ontology 输入或模型策略应建立新 run，保留旧哈希和来源。

对应机器记录：[goals.json](goals.json)、[work_packages.json](work_packages.json)。
