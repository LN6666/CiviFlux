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
