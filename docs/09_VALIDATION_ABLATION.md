# 09 · 成果验证与消融：证明有用，不强迫正结果

A3/A4 的当前模型是托管 Featherless SimpleJev；生产付费调用按[用户决定](../execution/USER_DECISIONS.md)暂缓。免费 demo 或 replay 只能证明限定的协议与图应用，不算完整消融。

## 首先防止循环验证

把已输入的“封闭道路列表”再预测出来只能验证转换与约束执行；不是预测成功。把“哪些公交受影响”的官方名单先写入KG又当标签，会泄漏。把SUMO结果用作graph seeds，再用同SUMO结果证明Qwen System-One“发现影响”，最多是受控检索评估，不能声称独立现实准确率。

评估设置分开：
- **pre-screen**：仅知closure/network/既有关系，预测需检查哪些实体；oracle routing/SUMO affected set作为隐藏任务真值。注意固定关键设施不允许被模型筛掉。
- **post-analysis retrieval**：已有facts，判断是否找全与问题有关证据。标签应衡量资料检索，不声称物理预测。

每份实验写明自己的设置。

## 预注册数据分组

Synthetic：至少12个有独立答案的拓扑母题（双路、单桥、孤区、反向、换乘、同层/跨层、时间边界、车辆类别、数据缺失、零扰动、候选噪声、多关系）。每个4个参数变体，共48个scenario，按母题/走廊分组划train/dev/test，不能把几乎相同seed变体拆到两边当泛化。

真实R1：Helsinki CityRun公告、实体匹配、当前或历史snapshot明确区分。
真实F1：Kalasatama真实地点+显式assumed限制，直到补齐历史管制证据。

主结果先synthetic heldout与真实source replay。独立历史traffic observations缺失时V3不打分，不能用randomTrips补成“observed”。只两次真实事件不足以推广全欧洲。

## 对照矩阵

| ID | 路由/SUMO | 语义关系 | 图排序 | Qwen System-One | 检验什么 |
|---|---|---|---|---|---|
| A0 | 相同 | 无检索KG | 直接可达性/几何候选 | 无 | 纯GIS已能解决多少 |
| A1 | 相同 | typed KG | bounded reachability/explicit rule | 无 | 语义关系的增量 |
| A2 | 相同 | 同一KG | fixed typed PPR | 无 | diffusion增量 |
| A3 | 相同 | 同一KG | SimpleJev-conditioned typed PPR | 经授权的真实托管 policy 冻结 | System-One 增量 |
| A4 | 相同 | 同一候选事实 | 固定候选的 SimpleJev 相关性排序，无 PPR | 重用 A3 的同一冻结真实 policy | 是否其实不需要 PPR |
| A5 | 相同 | 同一KG | neutral / permuted type weights PPR | 重用同一冻结 policy，不重复付费调用 | 是否权重语义真的有效 |

primary contrast A2→A3；A0→A1、A1→A2、A4→A3为解释对照。不要对48scenario×所有alpha×多模型×城市全排列。先一个冻结profile+seed，再只对dev最敏感参数做有限敏感性（alpha0.7/0.85/0.95；epsilon0.1与0.25），test只跑选定配置一次；更改后新版本有记录。

## 指标

代码与routing：constraint violations必须0；mandatory facility check coverage100%；unknown/missing另外计数。
检索：Recall@10/20（有不足候选时同时报N与K）、MRR/nDCG仅有独立graded labels时，coverage按节点类型分层；topK为空/全负样本定义清楚。
固定网络：路径长度/时间与独立oracle误差、不可达precision/recall。
SUMO：paired travel-time delta、arrived/unfinished、队列变化，分别表明synthetic或measured。
SimpleJev：有效响应率、真实调用次数与预算、请求大小/服务返回 usage、实际 wall-time、cache hit、同一请求的漂移检查；托管权重/服务器版本未知时明确标注，概率校准只在充分独立标签上诊断。不臆造本地 GPU/显存或 forward-pass 指标。
工程：wall time、CPU、peak RSS、artifact大小、冷/热缓存；图只跑一次却每模式重复计费是不允许的。

按scenario/group输出原始指标，使用paired difference和按scenario聚类的区间；小样本只报告描述性区间，不吹统计显著。地区/低数据类型的漏检也报告，不能只报全局平均。

## 不操纵效果阈值

工程必须：A3 真正用到经授权的托管 SimpleJev；数学和功能正确；调用/费用与本地计算分开记账；A0–A5 可重复。生产调用未获授权时不得把本条判为已通过。
研究不强制：A3必须优于A2。如果A3无增益/变差，默认UI可保留A2，A3作为明确experimental选项，完整功能仍保留并如实写报告。不能为了漂亮PR删难案例或扩大prompt直到命中test。

## 真场景检验模板

R1 source replay：公告事实条目总数、可定位条目、方向正确数、precision of geometry review、time coverage、未确认车种/时间。人工review图和来源片段索引，而不是只附地图截图。

F1：verified incident facts、assumed restrictions名单、run覆盖的设施/网络、不支持的烟火/楼层分析、无法核验的响应时间。火灾公共位置不等于公开全部应急数据。

如获得观测：固定事件时段、前后/同星期控制日，检查weather/traffic baseline变化；校准与测试隔离，报告缺失计数器/定位误差/未观测路段。不保证这些数据能取得。

## 成果报告必须包括

comparison.csv/parquet、variant config、sample counts、split hashes、raw metrics、System-One policy/model hashes、negative findings、source/evidence cards、reproduce command、known limitations。结果不只放README的漂亮图。


## 外部项目比较不是A6

A0–A5仍是因果最清楚的内部实验。Urban Flow/TWA/CReDo/rescuePY/SUMO_LLM_Agent/FireCom 不增加成同一“总分A6”，因为任务、数据、校准和输出不同。按照 `docs/15_COMPETITIVE_BENCHMARK.md`：v1 完成功能矩阵、工程性能基线、至少一个可运行邻居的reproduction notes；论文阶段再增加1–2个共享子任务的公平外部基线。

新增 ontology ablation（不新增编号，嵌入A1/A2）：比较 `raw graph joins` 与 `typed operational ontology projection` 的 invalid relation rate、evidence trace completeness、scenario replay success，不能只看排名。
