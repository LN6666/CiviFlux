# 验证证据索引

## 当前实现

- `current_product_release.json`：当前严格 release 状态，`make release-check` 读取此文件；未完成的必要 gate 使命令返回非零。
- `wp0/product_core_junit.xml`、`wp0/ontology_review.md`：产品/独立参考检查及本体审查。
- `wp1/`：Helsinki 来源、数据构建与候选事件映射。`case_review.json` 保留人工核验缺口。
- `wp2/`：实际路由与 PPR 场景运行摘要；`helsinki_boundary_sensitivity.json` 记录内圈→外圈的负面结果和外圈→第二外圈的受限稳定性，`helsinki_formal_boundary_case.json` 记录 48 个可配对目标的 Action→路由→KG→PPR 案例重跑。三处不能配对入口与两处重吸附入口仍未核验；`.runtime` 中的结果路径是本机证据，不假称已随 Git 分发。
- `wp3/`：SimpleJev 免费 typed API 原始响应、策略、provenance 与实际图应用；生产调用和校准仍未验收。
- `wp4/`：真实 SUMO 命令、输入、日志、输出、成功与失败记录；`rerouter_cycle_validation.json` 含有环路网多硬封闭反例。Junit 单列实际 simulator 检查。
- `wp5/`：两个 Web 宿主的真实浏览器检查、截图、导出包；`browser_lifecycle_cancel.json` 验证反复挂载和运行中取消。测试强制禁用模型 API。
- `wp6/`：冻结场景、独立标签/oracle、消融、内核 benchmark、外部开源系统 smoke；`policy_permutation_control.json` 是冻结真实免费策略的离线置换负对照，`historical_backtest_preflight.json` 仅盘点列名输入的历史证据缺口；`final_gate.json` 绑定代码与产物哈希。
- `wp7/`：最终检查、仓库卫生、干净检出和已安装 wheel 检查；`sbom/` 保存 CycloneDX 1.6、许可证清单、未决项与内容寻址 NOTICE 文本。`container_ci_initial_fail.json`、`container_ci_linker_fail.json`、`container_ci_atomic_fail.json` 保存三轮 Linux 容器失败；`container_ci_pass.json` 为随后 [PR #2 Linux CI](https://github.com/LN6666/CiviFlux/actions/runs/35898788800) 取得的真实 PASS 报告，限于无网络只读容器、合成需求和本地 API/SUMO。离线缓存缺失的首次结果与后续安装验证分别保留。
- `wp7/ci_run_36188723802.json`：PR #7 当前 Berlin 赛前基线锁定代码的受控 CI 回执，含测试数、确切 Git 树匹配、浏览器与容器产物哈希。它不含赛时观测或历史命中率。
- `events/berlin-2026-pre-onset-placebo.json`：两份真实官方 VIZ feed 的赛前增量安慰剂聚合统计、时间和原始字节哈希。道路级数据与 GIS 包仅存本机 ignored 路径；空间重合不是赛事命中。
- `events/berlin-2026-viz-mapping-audit.json`：官方封路通报线与 72 条 OSM 输入候选边的街名和几何重合审计，公开哈希与聚合数；方向和现场执行均未核验，逐段详情和地图只留本机 ignored 路径。这不是插件预测影响路段的命中率。
- `events/berlin-2026-mapping-sensitivity.json`：从原始赛前 VIZ 通报重新计算几何支持子集，将 8 条重合不足的已开始限制候选移出后，以原冻结城市包和 3 组 OD 复跑；六个基线/增量路由对象均未改变。仅是局部输入敏感性，不核验真实封路或赛时影响。
- `wp7/ci_run_36189858812.json`：当前安慰剂 GIS 代码树的受控 CI 回执，含 16 项浏览器测试、容器复现、确切 Git 树匹配和产物哈希；不把本机原始 VIZ 数据或 26 Sep 赛时结果冒充 CI 内容。
- `wp7/ci_run_36191842277.json`：公告几何映射审计与 GIS 分色代码树的受控 CI 回执，含 17 项浏览器测试、容器复现、确切 Git 树匹配和产物哈希；1 项 CI data 用例仍因 ignored Helsinki 数据缺失而跳过。
- `wp7/ci_run_36192737662.json`：柏林公告映射不确定性复跑代码树的受控 CI 回执，含 17 项浏览器测试、容器复现、确切 Git 树匹配和产物哈希；1 项 CI data 用例仍因 ignored Helsinki 数据缺失而跳过。其结果只验证固定三组 OD 对 8 条候选输入边的敏感性，不构成真实赛事命中率。

## 原始工程包参考证据

本目录根部的 `product_release.json`、`PACK_TEST_REPORT.md`、`pack_status.json`、`reference-*`、`pack-audit.txt`、`qwen-systemone-smoke-blocked.txt` 等是**导入工程包的历史快照/测试 fixture**，不代表现在的产品状态。原始参考测试明确读取旧 fixture，因此不改写其数学 oracle 或“当时尚未实现”的输入样本来迎合当前实现；当前 release 状态使用单独文件。

`PASS_PROTOCOL_ONLY`、`PASS_LIVE_POLICY_GRAPH_ONLY`、`PASS_UNBLOCKED_ENGINEERING_SCOPE` 都是限定范围标签，不等于完整 v1。模型评分不是事件概率，当前数据不是历史真值，单个起点不可达不能推出全城设施隔离。
