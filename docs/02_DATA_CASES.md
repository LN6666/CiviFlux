# 02 · 首城 Helsinki：公开事件、公开数据与证据边界

研究核验日期：2026-09-23。选择 Helsinki 是因为找到**具体道路活动公告 + HSL 官方公交/OSM 开放数据入口 + 同城真实火灾报道**，不是因为证明它比其他城市更好。

## Road Case R1：Helsinki City Run 2026-05-15–16

市政府于 2026-05-11 发布公告，列出南向 Mannerheimintie（Opera 至 Pohjoinen rautatiekatu）、Helsinginkatu（Mannerheimintie 至 Sturenkatu）、Mäntymäentie 等受限道路；另列 Baana 步行/骑行的时间。[S01]

**只复述已给出的限制；不能把 Baana 的小时范围赋给所有机动车道路。** 公告说明“计划中的限制”，不是实际实施 GPS 记录。Mäntymäentie 日期范围不能自动提升为精确起止小时。

文件 `cases/helsinki_cityrun_2026/case_evidence.json` 已预置事实候选，未编造 OSM way IDs、坐标、车种豁免或完整真实限行时间。

R1 在 WP1 必须转为可运行案例：下载路网→定位公告端点→选择有向 road segments→生成 review map→核对人工映射→保存每个匹配证据/不确定字段→必要时以一个明确“假设这些已公告限制同时有效”的 snapshot 运行。时间不完整时该 snapshot 是 what-if，不叫历史逐分钟 replay。

## Fire Case F1：Kalasatama / Leonkatu 公寓火灾

Yle 依据其取得的事故说明报道，事件位于 Leonkatu 公寓楼，通知时间为当地 20:55；报道涉及四层阳台。[S02] 当前方案只使用地点、通知时间等事件事实；不使用居民身份、不分析责任和原因，也不复制新闻全文。

**现有证据不包含可直接验证的完整封路几何、实际警戒区、消防车 GPS 和独立交通延误。** 另篇原始报道的图片说明明确写明火灾发生于2026-05-23，已核实日历日期。[S21] 门牌/坐标仍需核实；不得只凭街名捏造建筑中心点。

F1 分两部分：
- `incident_facts`：新闻/官方来源确认的真实事件事实。
- `scenario_assumptions`：用户画出的道路限制/警戒区及有效时段；明确标成 assumed，不自动生成安全半径。

因此 F1 初始验收名称是 **“真实地点火灾情景分析”**，不是“历史火灾交通预测已验证”。若后续取得真实管制/公交公告，再升级对应字段证据，不升级不存在的其他证据。

## 公共数据

### OSM 路网/设施

官方 HSL 数据页提供 OSM 区域提取入口；读取该目录获取实际文件名，再 pin 下载 URL+sha256。[S03] 主数据可包含道路、医院、消防站、公共交通站点；OSM 数据遗漏与 outdated tags 要明确报告。

历史事件优先使用截至事件前的快照。有可合法获取的历史快照则 pin；否则 current snapshot 只能用于 **current-network reconstruction / stress test**，不可写为2026年5月历史实况。不得利用事后更新的医院/路网静默增加准确度。

不要为了裁切小区域提前破坏长距离绕行。为整个候选情景留外圈路网；实际裁切半径通过扩大边界稳定性测试决定。

### HSL GTFS

官方最新 ZIP：https://infopalvelut.storage.hsldev.com/gtfs/hsl.zip 。官方说明每日更新并面向未来约两个月，因此当前下载不是历史时刻表。[S03]

每次记录 feed_start/end 或从 calendar 验证覆盖。历史 feed 找不到时，R1 的历史公交状态必须 NOT_VALIDATED；可另外展示当前 feed 下的反事实影响，不混在历史预测分数里。

HSL 页面说明其数据多数 CC BY 4.0，而 OSM 衍生数据有 ODbL，必须按实际源做 attribution。[S03] 不把可下载等同于可随意镜像。

### HFP/GTFS-RT/真实计数

实时接口存在不等于有公开历史归档。HSLdevcom/hfp-analytics 的 README 自述 API 当时非公开，不能将该 repo 当成可下载历史 GPS 数据。[S07]

HRI 有 Helsinki 交通量数据目录 [S08]；本次仅找到目录，没有核验该事件日期与路段的可用文件。WP1 最多两轮源核查：拿到真实文件，检查 timestamp、计数器坐标、车流/速度单位、许可、事件前后覆盖，再决定能否用于 outcome validation。没有就明确停止，不反复抓取或虚构。

## 数据落地流程

1. `fetch --source <registry_id>` 下载到临时文件；HTTP类型/长度/超时/总量限制；SHA256；原始字节不改写。
2. `inspect` 生成源日期、extent、CRS、行数、对象类型、许可、异常和未知；未知不自动修复成默认值。
3. `normalize` 产生版本化实体ID、geometry refs、edge IDs、road↔SUMO mappings、GTFS coverage。
4. `verify` 产生人工可查的端点/有向路段地图与 CSV，记录 reviewed_by、review_method。代理自检不得冒充独立人类专家。
5. `freeze` 冻结 citypack 和评估 labels；模型只读取 inference allowlist，不读取 heldout outcomes。

当前容器直接下载外部数据因网络/DNS限制失败；本包**没有附带完整 Helsinki PBF/GTFS**。官方网页核查已完成，但 `bytes_downloaded=false`。WP1 的文件级验证必须在开发环境真正执行。

## 数据规模目标（项目预算，不是测量结论）

目标 reference pack：先以覆盖事件及替代路径的城区/城市路网验证，不承诺“全城都被准确模拟”。路网10万有向边、semantic graph约20万边作为第一组性能测试；扩大只在边界/性能报告支持时做。内存、耗时以实测填写，不给未经跑分的秒级承诺。

## 结果验证三层

- V1 源事实/拓扑：公告道路匹配、车向、时段精度、设施 snap、限制编译正确。
- V2 独立运行变化：独立公交管制通告、道路开放/关闭记录；推理输入中不可提前包含作为 heldout target 的最终受影响路线名单。
- V3 数值预测：事件时段传感器/公交实测延误，加前后基线和对照日/控制区域；无数据不评分。

R1/F1 真实案例各写一张 data/evidence card；不得一律叫“real world validated”。
