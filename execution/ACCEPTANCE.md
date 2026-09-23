# 54 项目标验收与接手清单

更新：2026-09-24。状态对应 `execution/goals.json`；新补充的验证按具体范围记载，未完成的外部闸门继续保留。

**当前计数：** PASS 44，PARTIAL 8，DEFERRED_USER 1，BLOCKED_EXTERNAL 1；合计 54。不是 54/54 完成。

PASS 只覆盖该行写明的验收范围；PARTIAL 表示已有实现/证据但仍有条款未验证；DEFERRED_USER 是用户推迟的付费工作；BLOCKED_EXTERNAL 是来源/独立观测不可得。原始验收文本保留在 [goals.json](goals.json)，每项目标另列 assessment、remaining_steps 和证据。

## 当前决定与范围

- 以 [USER_DECISIONS.md](USER_DECISIONS.md) 为准：只用远程 Featherless SimpleJev `Qwen3.8-27B-classifier`，禁止本地模型下载/部署；普通 Qwen chat 不能替代 classifier。旧文档中的 local/Reflex gate 已明确覆盖。
- 免费 demo 共 3 次请求，真实 typed policy 已用于 toy/Helsinki 图，物理事实不变。这是集成证据；生产 paid 调用、独立专家语义标签、校准、模型优越性仍未通过。不要再次消耗免费配额或自动开启 paid。
- Ontology 仅服务 Road & Fire v1 所需概念、Actions 和投影；不扩展通用城市平台、调度、安全判断或 CFD。PPR 只表示 attention。
- 当前完整 Python 检查 225 项通过（包含 66 项原参考检查与本轮 SUMO/SBOM/置换专项检查），真实浏览器套件 10 项通过。两类检查不混称产品独立验证。native clean checkout/wheel 通过；[Linux CI](https://github.com/LN6666/CiviFlux/actions/runs/35898788800) 的 `core` 和无网络只读容器真实 API/SUMO smoke 均通过。
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
| G205 | 边界与不完整数据处理 | PARTIAL | 冻结 OSM 字节重建两层更大 Helsinki 路网；内圈→外圈 Road/Fire 各 48 个固定 OD 仍有 3/8 个阶段差异。按最小稳定外圈作为**48 个候选目标的案例边界**重跑 typed Action→路由→KG→PPR，外圈→第二外圈每案 96 个阶段在 1 秒阈值下差异为 0，已配对路径不变。共有边权重/转向仍变化，3 个入口无法配对、2 个原生入口会重新吸附；不可达值保持 null。 **待补：**独立核验/映射被排除的入口和重新吸附入口，完整原案例覆盖仍未通过；不作全城或历史收敛主张。 [helsinki_boundary_sensitivity.json](../evidence/wp2/helsinki_boundary_sensitivity.json)、[helsinki_formal_boundary_case.json](../evidence/wp2/helsinki_formal_boundary_case.json) |
| G206 | oracle和反例全覆盖 | PASS | 单向/桥/转向/平面交叉/no-op/车种反例和独立枚举 oracle 已执行。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[ablation_report.json](../evidence/wp6/ablation_report.json) |
| G207 | Road/Fire全部通过typed Actions形成Scenario overlay | PASS | Road/Fire 经 typed Actions 事务提交、记录、重放；失败不部分提交且 baseline 不变。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[ontology_review.md](../evidence/wp0/ontology_review.md) |
| G301 | 真实typed temporal KG投影 | PASS | 版本化 typed temporal 投影具来源、方向和有效窗；公交静态依赖与 operational 图分开。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[ontology_review.md](../evidence/wp0/ontology_review.md) |
| G302 | CSR PPR及独立oracle | PASS | CSR PPR 与 dense/NetworkX 独立数值 oracle 比较，mass/residual/dangling/alpha 检查通过。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[test_graph_ranking.py](../test_suite/unit/test_graph_ranking.py) |
| G303 | paired delta可比较 | PASS | 比较上下文、node universe/seed/policy/图哈希均校验，no-op delta 为 0。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[ontology_review.md](../evidence/wp0/ontology_review.md) |
| G304 | 真实远程 SimpleJev（用户覆盖） System-One协议与PPR pipeline | PARTIAL | 3 次免费 SimpleJev 请求取得真实 typed policy，并在 toy/Helsinki 图应用且物理事实不变；仅集成证据。 **待补：**生产 endpoint 真实验证须待用户另行启用 paid 配额。 托管服务器/权重版本未报告；专家语义标签、校准与泛化验证未完成。 [simplejev_graph_integration.json](../evidence/wp3/simplejev_graph_integration.json)、[systemone_simplejev_relations_policy.json](../evidence/wp3/systemone_simplejev_relations_policy.json) |
| G305 | 解释路径和类型内显示 | PASS | witness 引用实际图边且搜索有界；UI 按类型显示 attention，不冒充风险。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[ontology_review.md](../evidence/wp0/ontology_review.md) |
| G306 | 防装饰消融钩子 | PASS | neutral/no-PPR 分支及单一 relation 权重抵消反例保留。冻结真实免费 SimpleJev policy 的 720 种关系分数置换在合成图离线运行，物理 facts 固定、每种策略内 baseline/event 可比；事件图因单一关系权重抵消。它仅证明敏感性，不是 A3/A4 完整模型消融或排序质量增益。 [policy_permutation_control.json](../evidence/wp6/policy_permutation_control.json)、[offline_policy_permutation.py](../scripts/offline_policy_permutation.py) |
| G307 | Ontology ProjectionSpec生成scenario graph | PASS | 显式 ProjectionSpec 包含时间/空间范围/无隐含 hop 截断；audit/run/evidence 默认不进 PPR 并验证 hash。 [final_python_junit.xml](../evidence/wp7/final_python_junit.xml)、[ontology_review.md](../evidence/wp0/ontology_review.md) |
| G401 | 真实binary安装和adapter | PASS | 真实 SUMO 1.27.1 固定依赖，命令数组、日志和时间/车辆/输出预算已检查。 [validation.json](../evidence/wp4/validation.json)、[uv.lock](../uv.lock) |
| G402 | network/demand映射 | PASS | 有向 edge 映射、相同 seed/demand 和 synthetic 声明随 paired 运行记录。 [validation.json](../evidence/wp4/validation.json)、[sumo_pair.json](../evidence/wp4/sumo_pair.json) |
| G403 | hard closure/class运行 | PASS | 真实 SUMO 1.27.1 在有环合成路网执行两处硬封闭；编译为一个 rerouter，FCD 实际轨迹绕开封闭边且无循环。结论限于该反例与当前编译器。 [rerouter_cycle_validation.json](../evidence/wp4/rerouter_cycle_validation.json)、[test_multi_closure_rerouter.py](../test_suite/sumo/test_multi_closure_rerouter.py) |
| G404 | before/after metrics | PASS | 真实输出包含 arrived/unfinished/pending/teleported/rejected 及到达均值分母。 [validation.json](../evidence/wp4/validation.json)、[sumo_pair.json](../evidence/wp4/sumo_pair.json) |
| G405 | 取消和失败隔离 | PASS | 真实进程树取消、输出限额、失败隔离、坏 route 不发布成功产物已有检查。 [validation.json](../evidence/wp4/validation.json)、[final_python_junit.xml](../evidence/wp7/final_python_junit.xml) |
| G406 | Helsinki代表场景可跑 | PASS | Helsinki 有界代表走廊真实 SUMO pair 已运行，覆盖和未校准 synthetic demand 明示。 [helsinki_sumo_pair.json](../evidence/wp4/helsinki_sumo_pair.json)、[validation.json](../evidence/wp4/validation.json) |
| G501 | 同一Web Component两宿主 | PASS | 同一构建组件在 vanilla/MapLibre 两宿主经 5/3 次重挂载检查，释放订阅、中止请求、清理轮询和地图画布；未进行 OS/GPU heap profiling。 [browser_lifecycle_cancel.json](../evidence/wp5/browser_lifecycle_cancel.json)、[lifecycle-cancel.spec.ts](../web/tests/lifecycle-cancel.spec.ts) |
| G502 | 地图→scenario→运行 | PASS | 地图选择道路和导入显式火灾 polygon 均调用真实 Actions；时间/车种/assumption 确认可见。 [browser_validation.json](../evidence/wp5/browser_validation.json)、[workflow.spec.ts](../web/tests/workflow.spec.ts) |
| G503 | 进度取消失败体验 | PASS | 在受控同步点运行真实 RunService，浏览器点击 Cancel 后持久状态为 cancelled、结果端点 409，UI 无完成事件、结果请求或导出；模型出网关闭。 [browser_lifecycle_cancel.json](../evidence/wp5/browser_lifecycle_cancel.json)、[lifecycle-cancel.spec.ts](../web/tests/lifecycle-cancel.spec.ts) |
| G504 | 事实/attention/证据联动 | PASS | before/after 原始同尺度数值、完整设施 facts、witness 和 provider 状态可关联查看。 [browser_validation.json](../evidence/wp5/browser_validation.json)、[panel.ts](../web/src/panel.ts) |
| G505 | 导出与重放入口 | PASS | 实际下载 ZIP 包含 scenario/actions/ontology/result/manifest，token 排除和 Action 重放均已验证。 [browser_validation.json](../evidence/wp5/browser_validation.json)、[final_python_junit.xml](../evidence/wp7/final_python_junit.xml) |
| G506 | local安全/offline | PASS | host/origin/token、路径拒绝、job 隔离和浏览器零外部请求已有检查；首次依赖下载另行标注。 [browser_validation.json](../evidence/wp5/browser_validation.json)、[final_python_junit.xml](../evidence/wp7/final_python_junit.xml) |
| G507 | Object-centric Web View与Action UI | PASS | 对象 identity/state/links/facts/attention/evidence/actions/history 可读；用户经 Action，不直接编辑图。 [browser_validation.json](../evidence/wp5/browser_validation.json)、[ontology_review.md](../evidence/wp0/ontology_review.md) |
| G601 | 冻结48情景与独立labels | PASS | 48 个合成场景/12 母题分组冻结，独立枚举生成机器 labels，输入白名单阻止 heldout/标签流入模型。 [manifest.json](../experiments/frozen/manifest.json)、[ablation_report.json](../evidence/wp6/ablation_report.json) |
| G602 | 公平运行A0–A5 | DEFERRED_USER | A0/A1/A2/A5 共 192 行共享 48 套物理事实；A3/A4 共 96 行未跑；免费图 smoke 不能替代完整消融。 **待补：**待生产调用获用户配额授权且独立模型评估设计冻结后执行 A3/A4 及完整负对照；保持相同 physical cache。 [ablation_report.json](../evidence/wp6/ablation_report.json)、[final_gate.json](../evidence/wp6/final_gate.json) |
| G603 | R1源事实复现审计 | PARTIAL | R1 来源和机器候选映射审计已保存；human_accepted=0，source replay 未验证，时间未知保持未知。 **待补：**独立人工逐条确认道路边界/方向并记录 reviewer；来源缺失的时段/豁免保留 unknown。 [case_review.json](../evidence/wp1/case_review.json)、[directed_road_review.html](../evidence/wp1/directed_road_review.html) |
| G604 | F1真实地点情景审计 | PASS | 真实 Leonkatu 地点情景已运行，实际火场、管制和响应没有被冒称复原。 [case_review.json](../evidence/wp1/case_review.json)、[helsinki_fire_product.json](../evidence/wp2/helsinki_fire_product.json) |
| G605 | 如有观测则独立数值验证 | BLOCKED_EXTERNAL | [回测协议](../docs/HISTORICAL_BACKTEST_PROTOCOL.md)把来源事实、事发时网络、独立运营影响和独立数值观测分开；[只读预检](../evidence/wp6/historical_backtest_preflight.json)显示 R1 人工接受映射 0/3、F1 实际警戒区未知、历史 GTFS 不覆盖、独立实测目标 0。数值验证继续 `NOT_VALIDATED`；两次外部来源访问失败后停止。 **待补：**取得事件日期/地点/方向/单位/时间覆盖匹配的独立观测及对照后才能评价数值，当前不为该缺口空转。 |
| G606 | 成本性能与负结果 | PASS | raw metrics/latency/RSS/预算和分组描述区间已保存，明确非置信区间/非端到端性能，无模型增益主张。 [ablation_report.json](../evidence/wp6/ablation_report.json)、[benchmark.json](../evidence/wp6/benchmark.json) |
| G607 | 竞争功能矩阵与公平benchmark/reproduction | PASS | 152 格 source-backed matrix、内部 200k-edge benchmark、固定外部 OSS 真 smoke 与限制均保存，不作异任务总分。 [feature_matrix.csv](../comparison/feature_matrix.csv)、[SUMO_LLM_Agent.md](../comparison/reproduction_notes/SUMO_LLM_Agent.md) |
| G701 | clean checkout重建 | PASS | 当前代码提交 `ada0475` 的 macOS 干净 Git 导出在**已有冻结依赖缓存**下完成离线非 editable wheel 安装、toy 路由/PPR、wheel 构建及隔离导入；这不是新机器冷缓存离线证明。[GitHub Linux CI 35919129902](https://github.com/LN6666/CiviFlux/actions/runs/35919129902) 在相同受控代码树构建固定 base 的 amd64 镜像，记录本地镜像内容摘要（未发布 registry 镜像），在无网络只读容器完成真实 API/export 与合成需求 SUMO 1.27.1 smoke，原生 SUMO/netconvert 无缺失库。此项不验证历史城市影响或付费模型；早期失败证据保留。 [clean_checkout_ada_offline.json](../evidence/wp7/clean_checkout_ada_offline.json)、[ci_run_35919129902.json](../evidence/wp7/ci_run_35919129902.json) |
| G702 | 全部must gates | PARTIAL | contracts/network/graph/PPR/SUMO/web/security/reproduce 有实际通过；全部 must gates 尚未满足。 **待补：**处理 production SimpleJev/完整消融与人工真实城市映射缺口；strict release-check 仍按预期非零。 [current_product_release.json](../evidence/current_product_release.json)、[release_check_after_container.log](../evidence/wp7/release_check_after_container.log) |
| G703 | 独立审查与mutation | PASS | 独立子代理审查保留原反例，typed/context/hash/事务/witness/Object View 修复后回归通过；不是人类专家审查。 [ontology_review.md](../evidence/wp0/ontology_review.md)、[final_python_junit.xml](../evidence/wp7/final_python_junit.xml) |
| G704 | 许可隐私与数据分发 | PASS | CycloneDX 1.6 SBOM 包含 47 个 Python、99 个 npm 锁定包及本机 437 个原生文件哈希；机器可读清单保存 116 个许可证/NOTICE 文本，未知许可归属显式列出。架构/锁一致性及篡改反例通过；不作法律兼容性或跨平台原生文件审计结论。 [bom.cdx.json](../evidence/wp7/sbom/bom.cdx.json)、[license_inventory.json](../evidence/wp7/sbom/license_inventory.json)、[unknown_licenses.json](../evidence/wp7/sbom/unknown_licenses.json) |
| G705 | 完成用户文档和演示 | PASS | 当前 README/runbook/architecture 及截图覆盖本地安装、模式、证据和负结果；旧手交文档以用户决定和当前文档为准。 [README.md](../README.md)、[CURRENT_RUNBOOK.md](../docs/CURRENT_RUNBOOK.md) |
| G706 | 准确声明完成与缺口 | PASS | 工程部分验收与历史观测声明分开；记录 paid 推迟和已授权 GitHub 发布，不宣称 v1 全部完成。 [STATE.md](../execution/STATE.md)、[USER_DECISIONS.md](../execution/USER_DECISIONS.md) |
| G707 | Ontology/竞争比较发布审计 | PARTIAL | ontology/action/replay/projection、外部比较、NOTICE、SBOM 和 Linux 容器复现已有证据；完整 release artifacts 仍缺外部及付费模型 gates。 **待补：**完成 G702 后再签完整 v1 发布包；目前交付只能标明部分验收。 [ontology_review.md](../evidence/wp0/ontology_review.md)、[feature_matrix.csv](../comparison/feature_matrix.csv)、[bom.cdx.json](../evidence/wp7/sbom/bom.cdx.json) |

## 接手顺序

1. 先读本清单与用户决定，再查看 strict [release manifest](../evidence/current_product_release.json)。发布源码已获用户授权，不代表全部 v1 gate 通过。
2. 独立专项检查已补齐组件重挂载、浏览器取消、多硬封闭环路反例和 SBOM；Linux CI 的 Docker 构建及无网络只读容器 smoke 已通过。不要因此扩展 ontology 或产品范围。
3. Helsinki 内圈→第一外圈的固定 OD 曾出现差异；已选第一外圈对 48 个可配对目标重跑真实 Action→路由→KG→PPR，且与第二外圈比较在 1 秒阈值下稳定。仍需人工确认不能配对/重新吸附的设施入口及公告边界/方向，不能扩展为全城主张。历史数值验证必须取得合格观测；无数据时维持 NOT_VALIDATED。
4. 生产模型工作保持 DEFERRED_USER；用户明确启用配额后才做真实 A3/A4、冻结 policy/负对照和独立语义评估。专家标签与合成路径 oracle 是不同证据，不可互换。
5. 复用未变输入/源码的证据；只运行受后续变更影响的检查。更改 ontology 输入或模型策略应建立新 run，保留旧哈希和来源。

对应机器记录：[goals.json](goals.json)、[work_packages.json](work_packages.json)。
