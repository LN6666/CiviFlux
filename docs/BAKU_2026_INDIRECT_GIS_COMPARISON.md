# 巴库 F1：可视化间接对照

本地图只对照**两个公开计划**与一个有明确假设的插件运行：赛事方的普希金街封路公告 → CiviFlux 在 18 Sep OSM 有向路网中的两组**合成起终点**条件路由 → AYNA 独立公告中选出的市中心改线街名。该公交比较仍使用原机动车城市包和 `bus` 权限；新增的步行/骑行专用通道与步行区域来自独立的多方式候选包，用于显示网络候选；另有一个**明确假设**的步骑走廊敏感性探针。赛事真实步骑限制仍无逐段证据。它不是赛时车速或实际公交轨迹，也不输出“预测准确率”。

## 地图怎么读

打开 `web/baku-indirect.html`：红色为从[Baku City Circuit 2026 公告](https://www.bakucitycircuit.com/news/additional-traffic-options-to-be-provided-during-formula-1)映射的普希金街封路**候选**；蓝色虚线是无该候选封路的合成路由；橙色是加入候选封路后新出现的路段；青色虚线是[AYNA 2026 公交改线公告](https://www.ayna.gov.az/az/news/formula-1-azerbaycan-qran-prisi-ile-elaqedar-bir-sira-marsrutlarin-hereket-sxemi-deyisdirilir-1229)选出的街名在 OSM 中的候选几何；绿色是橙色路段中与 AYNA **独有街名**精确相同的部分。另有紫色步行专用线、玫红色自行车专用线、粉紫色共用线与淡紫色 OSM `highway=pedestrian + area=yes` 区域，**只表示 18 Sep 快照中的候选几何，不表示赛事造成影响**。深紫/深粉粗线是另一个 15 米假设走廊内的步行/骑行线性暴露候选，虚线为固定合成起终点的基线路径；深紫填充面专供显示假设走廊与步行区域的实际几何交集。本例交集为空，图层没有要素。这些都不是现场测量。点击线段可看图层语义、街名和有向路段 ID；图层可单独开关。

这张图的预设由[追踪的案例卡](../data/event_cases/baku-f1-2026-indirect-plan-case.json)固定。BCC 公告是唯一的封路情景输入。脚本没有读取 AYNA 街名来选择封路边或起终点，只在路由算完后作对照；但起终点是事件之后人工设定的，并非盲测抽样。普希金街本身和公告中作为边界的 Neftçilər 不计入“AYNA 独有街名”重合。完整赛道封路、其他车种例外与公交路线几何均未录入这个子案例。

## 当前可直接核对的数字

固定的 BCC 普希金街范围映射为 **12 条未人工审阅的有向边**。两组合成公交车种路由的无封路基线均穿过其中 8 条；加入候选封路后，分别多绕 **1,097.5 m / 59.6 s** 和 **851.6 m / 41.9 s**（OSM/SUMO 静态自由流成本，不是实测时长）。两组路由共有 **32 条去重后的新增绕行有向边**；其中 **23 条**位于 AYNA 另行公告的 `28 May küçəsi` 和 `Azadlıq prospekti` 街名之上。若只问这个代理比例，**23/32 = 71.9%**。它是**街名级间接重合比例，不是实际命中率**：公告没有逐段方向、起终点、时刻或实际轨迹，且 OSM 如何切分有向边会改变分母。[机器生成的汇总](../evidence/events/baku-2026-indirect-plan-comparison.json)保留数据与来源 SHA-256、每组 OD 的节点和数值。

同一 OSM 源另构建了[独立多方式 CityPack 与类型化 KG 审计](../evidence/events/baku-2026-multimodal-kg-audit.json)：共 95,904 条有向线性通道，其中 15,990 条没有机动车权限、仅有步行或骑行权限。地图中央裁剪范围显示步行专用 422 条、自行车专用 35 条、步骑共用 0 条，较宽的地图范围另显示 4 处明确标记 `area=yes` 的步行区域。计数基于 OSM/SUMO 导入权限，**不等于实地开放状态**；未画出的路边人行道、过街设施、无几何的通行规则仍是数据缺口。多方式 KG 的转向连接带有车辆类别，可按 `bus`、`bicycle`、`pedestrian` 分别过滤；当前没有将赛事封路推断到非机动车网络，也没有步骑 PPR 或现场出行时间影响值。下面的步骑时间仅用声明的固定速度作条件情景计算。

## 步骑间接指标：假设走廊敏感性

[单独固定的探针卡](../data/event_cases/baku-f1-2026-active-indirect-case.json)复用上文两组合成起终点，不按结果挑选。它对未审阅的 BCC 普希金街机动车候选几何分别取 **0.2 m** 和 **15 m** 缓冲，把与之相交且 OSM/SUMO 允许相应方式的线性通道作为潜在暴露。0.2 m 是窄缓冲，仍会包含横穿道路的线段，不代表整段共线。随后通过类型化 `CreateScenario`、`AddRoadRestriction` Action 创建**假设**步行/骑行受限的不可变情景，重放验证 ActionRecord；这不是官方步骑封闭公告。0.2 m / 15 m 是在探索时选定的几何敏感性参数，不是事前冻结的预测模型。

| 假设范围 | 步行暴露有向通道 | 其中专用非机动车 | 骑行暴露有向通道 | 其中专用非机动车 |
| --- | ---: | ---: | ---: | ---: |
| 0.2 m 窄缓冲 | 11 | 0 | 11 | 0 |
| 15 m 缓冲 | 60 | 37 | 28 | 5 |

每种方式的两组固定 OD 中，第一组基线可达，在两种假设缓冲下都变为**当前导入图上不可达**；第二组基线就不可达，不能计算新增扰动。步行基线为 212.76 m，按显式假设 **1.4 m/s** 得 151.97 s；骑行基线为 225.16 m，按 **4.0 m/s** 得 56.29 s。先前路由器错误地复用机动车速度，本次改为方式专用的固定速度假设；这些秒数不是实测。骑行第一组终点吸附距离 29.9 m；未审查的过街连接、路边人行道、赛时临时通道、外围网络及 OD 真实性都可能改变可达性。步行区域面不参与路由。

新增的区域面间接指标对固定 OSM ROI 内 **60 处**明确标记的 `highway=pedestrian + area=yes` 候选多边形逐个检查，0 个无效。与 0.2 m / 15 m 假设走廊有正面积交集的均为 **0 处、0 m²**；最近区域距走廊分别为 **220.28 m / 205.48 m**。因此这个限定的普希金街走廊探针不能把步行区域面计入受影响对象。这个负结果不排除赛事其他封路或更远范围内的步行扰动，也不能说明区域实际开放状态。区域面仍是来源绑定的地图候选几何，尚未进入可路由 KG。[完整逐 OD、来源哈希、ActionRecord 和重放结果](../evidence/events/baku-2026-active-indirect-probe.json)与[地图叠加 GeoJSON](../web/public/validation/baku-active-indirect.json)可复核。**不能从这些数字计算真实命中率。**

## 本机重建

```bash
PYTHONPATH=core:. uv run --frozen python scripts/baku_indirect_map.py
PYTHONPATH=core:. uv run --frozen python scripts/baku_active_indirect_probe.py
npm --prefix web run dev
```

仓库已包含[派生公交地图数据](../web/public/validation/baku-indirect.json)和[步骑假设叠加数据](../web/public/validation/baku-active-indirect.json)，所以常规前端启动后可直接打开 `http://127.0.0.1:5173/baku-indirect.html`。要**重新生成**数据，本机须有[数据 README](../data/README.md)所述、哈希固定的机动车与多方式 Baku CityPack、后者的 `roads.osm.xml`，以及两份原始公告 HTML；脚本会先核查 CityPack 与公告字节。大型 OSM CityPack 与公告原文不随仓库发布。地图道路几何为 © OpenStreetMap contributors，ODbL 1.0，来自 Geofabrik 2026-09-18 Azerbaijan 提取；[数据许可与署名](https://www.openstreetmap.org/copyright)独立于项目代码许可。

## 下一层对照

若取得可合法使用的赛时实际公交 GPS/道路速度，再新增**实测图层**并逐有向路段匹配；当前 AYNA 公告不能替代那层。若只有路段现况，可核对位置；要量化相对封路前的车速差，还需可比的先前或历史同小时观测。
