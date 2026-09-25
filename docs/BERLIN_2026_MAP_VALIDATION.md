# 柏林马拉松：插件路段与实际交通的 GIS 对照

打开 `web/validation.html`，在同一张地图上看灰色道路背景、深橙/浅橙的插件受影响路由路段（分别有/无赛前 VIZ 几何覆盖）、紫色虚线情景输入封路候选、深蓝虚线赛前匹配的对照路段、蓝色柏林 VIZ 赛事封路通报、VIZ 实时交通状态。接入赛时快照后，**绿色**显示预测命中、**红色**显示实际变化未被预测、**紫色实线**显示预测处未测得变化；无赛前数据或缺速的路段不评分。变化指新标记封闭或平均车速降低至少 30%。点击路段可查 ID、来源、时刻和车速。图层可单独开关。

## 已冻结的比较对象

- [赛前插件路由结果](../evidence/events/berlin-2026-incremental-pre-onset-probe.json)在 2026-09-25 18:20 UTC 冻结，早于 26 日 07:00 CEST 的官方计划新增限制。两个东西向 OD 的原路由共有 **51 条去重后的有向路段**作为插件预测影响图层；北南对照 OD 不变。
- [公告映射候选](../data/event_cases/berlin-marathon-2026-closure-candidates.json)是输入，72 条有向路段，地图上用紫色展示，不计入插件预测输出。
- 2026-09-25 18:45 UTC 已抓取[柏林 VIZ 实时交通 WFS](https://api.viz.berlin.de/geoserver/mdh/ows?service=WFS&version=2.0.0&request=GetCapabilities)于固定边界 `13.33,52.50,13.44,52.55`，获 1,991 个方向路段；同次[官方交通通报 GeoJSON](https://api.viz.berlin.de/tic3/baustellen_sperrungen_tic.json)有 6 条马拉松相关记录。抓取回执在本机 ignored `data/raw/berlin-validation/sep25-pre-event-evening-receipt.json`，交通 SHA-256 `50cce2b3e0d1a8a699b0e9fa70ec98f7629fb1a2ecd1955887308d160ad0884b`。这是**赛事增量开始前**的交通状态，不能报赛时命中率。

## 赛前可测覆盖审计

### 公告几何与道路候选的间接核查

把 25 Sep 18:45 UTC 的 6 条 VIZ 马拉松封路通报线与[公告映射候选](../data/event_cases/berlin-marathon-2026-closure-candidates.json)逐段比较。先要求街名相同，再要求 OSM 候选边至少有 `min(25 m, 边长的 25%)` 落在某一条通报线的 18 m 缓冲区内。[公开聚合审计](../evidence/events/berlin-2026-viz-mapping-audit.json)记录候选文件、CityPack 与 VIZ 通报的 SHA-256：已开始的 Straße des 17. Juni 案例 **29/37** 条有向候选边达到空间重合阈值，**8/37** 条没有；其中 30 条离同街名通报线不超过 18 m，说明 1 条虽近但重合长度不足。已排定 26 Sep 增量的 Unter den Linden 案例 **0/35** 条获得此快照的同街名通报支持，因为该快照**没有同街名 VIZ 通报**；这不等于公告错误或道路未封闭。72 条有向边中方向核验均为 **0**，全部维持 `CANDIDATE_UNREVIEWED`。这项核查只帮助发现公告→OSM 映射疑点，不能充当插件受影响路段的命中率或现场封路证据。

本机可生成逐段审阅图，蓝色为 VIZ 计划通报，紫色为有空间支持的输入候选，红色为有同名通报但重合不足，灰色为此快照无同名通报；橙色仍是**独立的插件预测路线**。点击候选可看距离、重合长度、阈值和道路 ID。原始通报几何、逐段审计和地图包都留在 ignored 本机路径；公开仓库只保存上述聚合审计：

```bash
uv run --frozen python scripts/berlin_mapping_audit.py sep25-pre-event-evening
npm --prefix web run dev
```

浏览器打开 `http://127.0.0.1:5173/validation.html?bundle=mapping`。VIZ 通报是事先发布的计划几何，不能核验有向道路权限、现场执行或交通扰动。

用上述**同一份赛前快照同时充当比较器两侧**进行空变化负对照：51 条冻结插件路段中，按 18 m 缓冲、方向与重合长度规则，**25 条**至少匹配一个 VIZ 路段，**26 条无 VIZ 空间覆盖**；与插件路段匹配的 VIZ 有向 ID 为 **12 条**，其中 **11 条**的赛前状态可评分。固定预测周围 1 km 范围共 420 条 VIZ 路段，375 条可评分，45 条已封闭或字段缺失。空变化控制没有产生状态变化命中或漏报。此审计只说明赛时对照可能覆盖的观测范围，不评价插件准确率；无 VIZ 覆盖的 26 条不能被记为误报。[可复核摘要](../evidence/events/berlin-2026-viz-pre-event-coverage.json)只公开哈希与统计，原始 VIZ/HERE 几何仍留本机 ignored。重新生成：`uv run --frozen python scripts/berlin_pre_event_coverage.py`。

同一 25 Sep 赛前快照也用来**预检对照选取是否可行**：在 11 条有可评分赛前状态的预测重合 VIZ 路段中，11 条各找到 2 条未重复的对照，共 22 条。选择只使用赛前 VIZ 道路类别、方向、自由流车速、当前车速比和几何长度；对照位于冻结预测 1 km 范围内，距预测路线及输入封路候选至少 200 m，本次最小实测几何间距 211.2 m。选择清单的 SHA-256 与输入快照哈希写进同一[审计摘要](../evidence/events/berlin-2026-viz-pre-event-coverage.json)，具体 VIZ 路段几何/ID 留在 ignored 本机包。**这只是方法可行性预检**：实际 26 Sep 赛前快照会重新固定对照，可能出现不同数量；远离路线也不保证未受赛事溢出影响。

## 新增限制前的安慰剂对照

25 Sep 18:45 与 21:03 UTC 再取两份**真实、相互独立**的官方 VIZ 快照；两份 feed 均早于 26 Sep 05:00 UTC 的新增限制起点。使用完全相同的路段匹配和 30% 降速/新增封闭规则，在 375 个可评分 VIZ 路段中有 1 个背景变化与冻结预测路段重合、13 个邻近背景变化未重合、10 个预测重合处未见大变化；45 个不可评分。14 个变化由 13 个降速和 1 个新增封闭组成。11 个有效预测—对照组的相对降速差中位数为 **0.0 个百分点**。这说明仅凭后续两时刻的空间重合就报“命中”会混入已有变化；它不是赛事开始后的命中率，也不是校准后的误报率。这段时间其他马拉松准备/封路已经存在，且两次快照相隔约 2 小时 18 分钟。[公开聚合证据](../evidence/events/berlin-2026-pre-onset-placebo.json)保留来源哈希、时间和统计，不公开原始 VIZ/HERE 路段。

本机可重建 ignored 安慰剂 GIS 包：

```bash
uv run --frozen python scripts/berlin_validation_map.py placebo sep25-pre-event-evening sep25-late-evening-placebo --output web/public/validation/berlin-placebo-local.json
npm --prefix web run dev
```

浏览器打开 `http://127.0.0.1:5173/validation.html?bundle=placebo`；颜色图层在该状态下标为赛前背景变化，不显示赛事精确率/召回率。两份原始快照均位于 ignored `data/raw/berlin-validation/`，仅有聚合证据随 Git 分发。这个安慰剂不替代下面计划中的 26 Sep 赛前冻结与赛时配对。

## 本机运行

```bash
uv run --frozen python scripts/berlin_validation_map.py capture sep26-pre-0700-cest
uv run --frozen python scripts/berlin_validation_map.py build sep26-pre-0700-cest --output data/raw/berlin-validation/sep26-pre-0700-cest-baseline-map.json
uv run --frozen python scripts/berlin_validation_map.py capture sep26-event-0830-cest
uv run --frozen python scripts/berlin_validation_map.py build sep26-pre-0700-cest --event-name sep26-event-0830-cest
npm --prefix web run dev
```

前两条均须在 2026-09-26 **07:00 CEST 前**完成；第三条在限制开始后执行。事件建图必须读取第二条保存的基线包，并校验其建成时间、原始快照、预测/城市包哈希与对照选择完全一致，否则拒绝产出事件比较。抓取和建图还核对回执与 WFS 正文的 feed 时间戳、路段数及 15 分钟新鲜度；不能用任意较晚或过期的快照伪装赛前记录。浏览器打开 `http://127.0.0.1:5173/validation.html`。脚本只读取官方 WFS/GeoJSON；原始快照、基线包和 `web/public/validation/berlin-local.json` 均被 Git 忽略，地图在浏览器本地加载，不把 VIZ/HERE 原始路况重新发布到公开仓库。需要分享成果时，可分享代码、来源、SHA-256、各路段统计和获得再分发许可后的图件。

## 逐段差异怎么算

两次快照按 VIZ `unique_id` 配对；重复 ID 拒绝评分。两份 feed 的实际 `timeStamp` 必须分别在 26 Sep 07:00 CEST 公告新增限制起点之前和之后，且各自距离本机抓取时间不超过 15 分钟；回执必须与响应正文时间戳一致。比较区域在赛前固定为插件预测路由几何周围 1 km；**只用赛前 VIZ 几何**判定某路段是否与预测重合：相距不超过 18 m、行驶方向一致（端点方向余弦至少 0.5），且至少 25% 或 25 m（取较小者）与缓冲带重合。赛时新增或移动的几何不能改变这个赛前覆盖分母。同 ID 的前后几何若反向或 Hausdorff 距离超过 25 m，或者赛时缺失该 ID，则标为不可评分，不把拆分/变形误作道路状态变化。若赛时新出现 `closed=1`，或两次都未封闭、车速均为正且车速下降至少 30%，标为“状态变化”。由此列出命中、漏报、误报及无赛前数据/原先已封闭/缺速的不可评分路段；精确率和召回率的分母只取可评分路段。红线和列表均保留每条路的原始 ID、前后车速、封闭字段及匹配结果，方便人工核对错配。

这里比较的是**两个实时时刻的交通图层变化与冻结插件路段的空间差距**。地图还报告 51 条预测路段中有多少条能与 VIZ 方向路段匹配；未覆盖的预测路段不能自动算作误报或命中。对照路段在赛前选定、赛时只按同一 VIZ ID 读取；双方都有效且未封闭时，另报“预测重合路段降速比例减去所配对照降速比例”的组内中位数。新标记封闭另计，不拿零车速算降速。这个间接指标可揭示部分共同的早晚时段变化，却不能排除赛事溢出、道路工程、天气、需求变化等差异；进一步归因仍需同星期/同小时基线或更强独立观测。蓝色封路通报可能事先发布，也不当作现场实测。当前 2026 逐小时检测归档尚未公开到[柏林检测归档](https://api.viz.berlin.de/daten/verkehrsdetektion)，故实时抓取时间窗不能错过。

## 当前缺口

截至 2026-09-25 21:03 UTC，只有新增限制前的两份快照。26 Sep 赛前冻结包、赛时快照、路段匹配复核及最终差距尚待赛事发生；当前安慰剂地图已经揭示背景变化，但尚无真实赛事命中率。生产 SimpleJev 订阅对此路由与交通对照不需要，仍保持付费调用禁用。
