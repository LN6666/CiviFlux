# 柏林马拉松：插件路段与实际交通的 GIS 对照

打开 `web/validation.html`，在同一张地图上看灰色道路背景、橙色插件输出的受影响路由路段、紫色虚线情景输入封路候选、蓝色柏林 VIZ 赛事封路通报、VIZ 实时交通状态。接入赛时快照后，**绿色**显示预测命中、**红色**显示实际变化未被预测、**紫色实线**显示预测处未测得变化；无赛前数据或缺速的路段不评分。变化指新标记封闭或平均车速降低至少 30%。点击路段可查 ID、来源、时刻和车速。图层可单独开关。

## 已冻结的比较对象

- [赛前插件路由结果](../evidence/events/berlin-2026-incremental-pre-onset-probe.json)在 2026-09-25 18:20 UTC 冻结，早于 26 日 07:00 CEST 的官方计划新增限制。两个东西向 OD 的原路由共有 **51 条去重后的有向路段**作为插件预测影响图层；北南对照 OD 不变。
- [公告映射候选](../data/event_cases/berlin-marathon-2026-closure-candidates.json)是输入，72 条有向路段，地图上用紫色展示，不计入插件预测输出。
- 2026-09-25 18:45 UTC 已抓取[柏林 VIZ 实时交通 WFS](https://api.viz.berlin.de/geoserver/mdh/ows?service=WFS&version=2.0.0&request=GetCapabilities)于固定边界 `13.33,52.50,13.44,52.55`，获 1,991 个方向路段；同次[官方交通通报 GeoJSON](https://api.viz.berlin.de/tic3/baustellen_sperrungen_tic.json)有 6 条马拉松相关记录。抓取回执在本机 ignored `data/raw/berlin-validation/sep25-pre-event-evening-receipt.json`，交通 SHA-256 `50cce2b3e0d1a8a699b0e9fa70ec98f7629fb1a2ecd1955887308d160ad0884b`。这是**赛事增量开始前**的交通状态，不能报赛时命中率。

## 本机运行

```bash
uv run --frozen python scripts/berlin_validation_map.py capture sep26-pre-0700-cest
uv run --frozen python scripts/berlin_validation_map.py capture sep26-event-0830-cest
uv run --frozen python scripts/berlin_validation_map.py build sep26-pre-0700-cest --event-name sep26-event-0830-cest
npm --prefix web run dev
```

第一条应在 2026-09-26 **07:00 CEST 前**执行，第二条应在限制开始后执行；不要用任意较晚的快照伪装赛前记录。浏览器打开 `http://127.0.0.1:5173/validation.html`。脚本只读取官方 WFS/GeoJSON；原始快照和 `web/public/validation/berlin-local.json` 均被 Git 忽略，地图在浏览器本地加载，不把 VIZ/HERE 原始路况重新发布到公开仓库。需要分享成果时，可分享代码、来源、SHA-256、各路段统计和获得再分发许可后的图件。

## 逐段差异怎么算

两次快照按 VIZ `unique_id` 配对。比较区域在赛前固定为插件预测路由几何周围 1 km；某 VIZ 路段若与预测几何相距不超过 18 m、行驶方向一致（端点方向余弦至少 0.5），且至少 25% 或 25 m（取较小者）与缓冲带重合，视作空间重合。若赛时新出现 `closed=1`，或两次都未封闭、车速均为正且车速下降至少 30%，标为“状态变化”。由此列出命中、漏报、误报及无赛前数据/原先已封闭/缺速的不可评分路段；精确率和召回率的分母只取可评分路段。红线和列表均保留每条路的原始 ID、前后车速、封闭字段及匹配结果，方便人工核对错配。

这里比较的是**两个实时时刻的交通图层变化与冻结插件路段的空间差距**。地图还报告 51 条预测路段中有多少条能与 VIZ 方向路段匹配；未覆盖的预测路段不能自动算作误报或命中。若两时刻小时不同，普通日内流量变化也会进入结果；因此下一轮需要同星期/同小时基线或无赛事对照走廊，才能把红线进一步归因为赛事。VIZ 封闭字段为 1 时的零车速不当作车速测量；蓝色封路通报可能事先发布，也不当作现场实测。当前 2026 逐小时检测归档尚未公开到[柏林检测归档](https://api.viz.berlin.de/daten/verkehrsdetektion)，故实时抓取时间窗不能错过。

## 当前缺口

截至 2026-09-25 18:45 UTC，只有赛前快照。赛时快照、路段匹配复核及最终差距尚待赛事发生；当前地图是可操作的对照界面，尚无真实预测准确率。生产 SimpleJev 订阅对此路由与交通对照不需要，仍保持付费调用禁用。
