# 06 · 道路与火灾：建模边界和仿真实现

## Road v1

支持有向edge的时间窗全封闭、指定车种封闭、车道限制（有lane mapping才支持）；不完整lane数据返回unsupported，不能将降容偷偷改为全封。

基础路由输出是固定travel-time权重最短路差：`distance_m`, `travel_time_s`, `reachable`，不是实时拥堵预测。速度缺失时采用显式road-class假设profile，保存assumption，禁止LLM猜速度。桥梁/隧道平面相交不自动连通；设施入口与最近主干道路几何中心不同。

消防类车辆的权限、限高/宽、逆行、信号优先不从一个`emergency`标签自动推导。v1默认保守服从已知限制；由用户明示可通行的道路才能放行。消防站到事件的`network travel time`不是call handling+turnout+travel的总响应时间，也不代表该站有可用车组。

## Fire v1

火灾输入点/建筑轮廓、时间、人工/外部确认的限制区/道路。计算外部网络变化与potentially associated facilities。没有烟/热模型就不输出烟羽、死亡概率、传播时间、疏散安全性。事故点周边buffer只允许用于选择候选数据，不自动成为风险/封闭区。

用户明确录入的圈定区域用于道路限制候选，逐条确认方向和车种。禁止“中等火灾默认100m”这种伪消防标准。火灾假设不自动影响OD出行需求；需求变化只有显式参数且marked assumed才加入。

## SUMO paired runs

同一net文件、同一OD/demand文件、same random seeds、同一warmup和分析窗口。baseline与event只改变明确的restrictions（或单列demand变化因子）；不能每次randomTrips不同再比较。

显式记录network conversion options、signals assumptions、car-following配置、rerouting比例和knowledge假设。多scenario共用physical cache。

[S09]官方文档一个关键陷阱：`closingReroute` **不带allow/disallow是soft closure**，无替代路径的车可能继续走。hard closure必须使用权限并测试车辆日志。多rerouter配mode8有循环风险；统一同时段closures，禁止用全局ignore-route-errors掩盖输入错误。

默认对验证fixture禁用/严格记录teleport。生产report同时报告`arrived, unfinished, teleported, rejected_departures`，只平均成功到达车辆会偏差，不能把未到达算0分钟。设置最大simulation duration、max vehicles、wallclock timeout、output size、取消子进程树。

## 两类SUMO成果

- `SYNTHETIC_DEMAND_WHATIF`：可证明工具和情景机制工作，不能证明真实拥堵数值。v1必须至少提供这种真实SUMO运行。
- `CALIBRATED_MEASURED`：取得真实OD/计数，校准仅使用训练部分，再对独立事件/控制日验证。无数据不开放此badge。

## 必须的SUMO集成fixture

小型双通道网络：baseline皆可走，关闭短通道后车辆用长通道；唯一通道全封则未到达/等待；允许特定class仅该class可进入；closing起止边界；同时两处限制无循环；取消kill child；相同seed baseline重跑结果hash/数值一致；异常日志导致失败而不是地图绿色完成。

## 路网裁切

离事件近不代表受影响大，远端绕行可能关键。先路由边界A，再A+外圈，比较OD可达性、绕行时间、关键设施指标；变化超过预声明阈值扩大或标记未稳定。不能在建semantic graph前随意删掉医院所在外围区。
