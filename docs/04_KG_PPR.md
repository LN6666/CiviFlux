# 04 · 知识图谱与 PageRank：真正参与运算、可独立验证

## 不能装饰性“接上知识图谱”

v1 关系类型：ROAD_CONNECTION（从合法路网导出）、ROUTE_USES_SEGMENT、FACILITY_ACCESSED_VIA、STOP_ON_ROUTE、CELL_ACCESSES_FACILITY（有OD结果才建）、INCIDENT_RESTRICTS（事件元数据，可从PPR projection排除）、NEAR（仅候选关联）。

原始 source 事实与派生事实分开；关系的逆方向若需传播，显式建反向 relation，不能把所有边变无向。比如从受限道路寻找使用它的公交线，PPR投影要使用 `SEGMENT_USED_BY_ROUTE`，不能把逻辑方向写反。

图只保存ID、relation type、有效时间、来源与权重；geometry不进入每次Qwen System-One请求。projection保留 source IDs，可随时回到GIS图层检查。

## PPR 数学约定

固定 `alpha=0.85` 表示**继续沿边走**的概率，restart是1-alpha，与NetworkX API约定一致。[S10]

\[
r=(1-\alpha)s+\alpha P^T r,\quad \sum_i s_i=1,\quad P\mathbf1=\mathbf1.
\]

稀疏CSR power iteration为主；dense linear solve仅用于小图独立oracle。负值/NaN/inf直接拒绝。dangling row分配到s。要求数值测试 `mass_error<1e-10`、`residual_l1<1e-10`（小图），大图默认 `residual_l1<=1e-8`，保存实际值和迭代次数；不收敛不是PASS。

## relation-aware transition，不靠连接数量偷分

对节点i的一种关系t，先做关系内部归一化，再做关系之间混合：

\[
Q_{ij|t}=a_{ijt}/\sum_{k\in N_t(i)}a_{ikt},\quad
\pi_i(t)=m_t g_t/\sum_{u\in T_i}m_u g_u,\quad
P_{ij}=\sum_t\pi_i(t)Q_{ij|t}.
\]

`a` 是已定义的非负关系强度；未评估confidence仅做数据标签，不默认将数据贫乏区域的重要性乘为0。`m_t`为显式baseline profile，`g_t=epsilon+(1-epsilon)*score_t`，epsilon默认0.10作为待敏感性验证的工程参数，非科学常数。专家/规则硬排除的关系不让Qwen System-One重启。

同一出边只有一种relation type时，统一乘Qwen System-One分数会被行归一化抵消——**这是数学事实，不是接入失败**。必须提供含多种relation的fixture证明Qwen System-One能改变transition；也测试单一关系场景不变。不为了制造排名变化偷偷加随机扰动。

## before / after 可比性（最重要）

构建pair时取两张图的统一实体集合U，排序稳定，事件本身若只是元数据则两边均排除。相同 `s, alpha, m_t, g_t, normalization`、同一snapshot。被封闭道路仍可作为semantic asset存在；在routing graph禁止走，不意味着从KG删除被影响对象。

first use：将用户选择的road IDs映射成统一seed，baseline和event用同一s。需要按实际延误改seed的额外分析叫 `event_evidence_attention`，不能与原baseline直接叫纯delta。

\[
\Delta r=r_{event}-r_{baseline}.
\]

改变Qwen System-One objective/profile是独立policy ablation，不能混入closure effect。总和Delta为0；局部分数下降可能是其他位置得到更多概率质量，不能解释成该处风险下降。

## 为什么不直接把PPR叫影响

真正的延误/可达性由router/SUMO产出。PPR只用于在已有facts和关系里排序检索/浏览。先显示事实指标，再显示“关联关注度”。候选检索可以topK，但**不得用Qwen System-One/PPR裁掉固定必查的医院/消防设施**；硬规则检查和图排名分离。

## 解释

每条解释必须引用实际graph edge IDs和source refs。可输出2–3条贡献较大的有界walk或dependency witness，并注明“该路径支持关联解释，不证明物理因果”。

PPR完整概率来自所有walk；一条最短路径不是全部分数来源。选择做精确walk贡献时使用 `(1-alpha)*alpha^k*path_transition_product*seed_mass`，显示覆盖质量与截断上界；否则仅称witness path，不能捏造contribution%。

## 计算规模

完整路由边界与scenario semantic projection不同。优化先缓存/CSR/局部projection，不先写增量PPR。用扩大外圈检验critical metrics稳定；若不稳扩大或标记 boundary_truncated。人口网格到每个设施的全连接会爆炸，按明确OD/coverage需求建立有限关系，保留未分析范围。

## 必须消融

A0 GIS/router/SUMO；A1+typed reachability；A2+fixedPPR；A3+QwenSystemOnePPR；A4Qwen System-One-noPPR；A5permuted/neutral weights。具体公平比较在docs/09_VALIDATION_ABLATION.md。


## operational graph 与 dependency graph 的具体更新规则

事实层保留两列 `baseline` / `scenario`，不是覆写原始路网。对于有 verified 路径的设施/公交，分别从该时刻合法路径产生 operational dependency edges；改变后的路径可改变边集合/strength，统一实体集合U后计算paired PPR。每项变化写入 `graph_delta_log`，含原关系、变更后关系和对应router/SUMO fact IDs。

静态的“某公交历史上用此路段”仍可留在dependency evidence层，以便解释为何它可能受扰动；不能把它误当已经绕行后的实际路线。两个projection必须有不同`projection_kind`，禁止把它们无说明混合成一个分数。

若手头只有静态关系，缺少足以更新operational graph的资料，使用 `event-seeded attention` 即可；baseline/event图实际相同则delta=0，报告“无法由这些数据识别结构变化”。不凭空修改边权来制造影响。对用户最重要的可达性事实仍由router独立产出，不依赖PPR是否变化。

baseline指**同一分析时刻、同一外部条件但没有本次restriction**的反事实，不是昨天和今天随便两张图。Qwen System-Onepolicy变化实验只叫policy ablation，不叫事件delta。本包reference_outcomes演示的正是policy ablation，已用not_event_delta=true明确标记。


## Ontology projection boundary

从 handoff-3 起，typed KG 是 Operational Ontology 的**分析 projection**，不是全部 ontology。`Scenario`, `ActionRecord`, `EvidenceSource`, `SimulationRun` 等可存在于 ontology，但默认不进入 PPR。每次 ranking 保存 `ProjectionSpec`：允许 object/link 类型、时间、objective、policy 与 source snapshot hashes。

任何代码若直接遍历“全部 ontology links”生成 PPR 都必须被测试拒绝。Road/Fire Action 改变 scenario overlay，deterministic Functions 先产生 operational facts，再由 projection 构建 scenario graph。
