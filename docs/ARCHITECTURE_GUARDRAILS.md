# 架构约束与维护边界

依据：用户在 2026-09-24 指定的架构讨论第 9–20 节。以下是当前工程约束；讨论中的示意对象、算法及性能数字不是已验收功能或 SLA。

**Ontology must serve the application, not the other way around.** 本体只服务 Road & Fire v1 的道路限制、事件、设施可达性、公交依赖、场景、运行及证据。新增类型或接口的 PR 必须指向当前用例、输入来源和可验证输出。不能仅以“其他城市/未来插件可能需要”为理由加入类型。现有 registry 中 District、PopulationCell 等尚未实例化的类型不代表已经支持人口影响分析；不继续扩张它们。

| 风险 | 当前约束与检查位置 | 仍需诚实保留的边界 |
|---|---|---|
| 本体无限膨胀 | 单一 `ontology/manifest.yaml` 注册表；adapter 不得自创关系；typed endpoint 验证 | 不实现通用城市知识标准、插件继承框架或完整 RDF 平台 |
| 本体迁移破坏旧结果 | Scenario、ActionRequest、ActionRecord、ProjectionSpec、ResultBundle 记录 ontology_version；不支持的版本拒绝；快照、overlay、图及策略哈希绑定 | 尚无 v2，不能声称已实现未来破坏性迁移；见下文 |
| 数据映射与实体消歧 | OSM/GTFS 来源 ID、注册来源、跨类型唯一身份；设施入口与 route alignment 的候选状态保留 | 名称相似/地理接近不构成同一实体证据；跨源医院去重、人工入口核验尚未完成 |
| 图投影任意改变结论 | ProjectionSpec 保存类型、关系、目标、分析时刻、时间窗、snapshot、空间范围和 hop 规则；配对比较验证 spec 一致 | 当前范围是已冻结 citypack 全部对象，`max_hops=null`，并非隐藏的 5-hop 裁剪；边界敏感性单列 |
| PageRank 被解读为因果 | 物理 facts 与 attention 独立字段；witness 仅为依赖路径；不同类型内排名 | attention、delta、排名均不是风险、损失或事故概率；无独立观测时不作历史预测声明 |
| 模型判断伪装概率 | SimpleJev expected rubric index 归一化为 semantic relevance；保留 rubric、条件分布、provider/model/usage | 模型 confidence 不是正确率或物理概率；生产版本未经本项目校准 |
| 自我强化的解释 | 先独立计算 routing/SUMO，再计算政策与 PPR；政策不改变道路速度、封路或 SUMO 输入；单一关系归一化不变量测试 | PPR 的变化不能用另一次 LLM 评价作为独立有效性证据 |
| 语言模型幻觉 | v1 默认展示结构化 facts、路径与来源；导出机器可读证据；LLM 起草的 Action 必须由用户确认 | 可选解释器尚不作为事实来源；未来生成文本必须逐项绑定现有 evidence ID，缺失信息输出 unknown |
| 端到端延迟叠加 | routing 快速路径与 routing_sumo 显式分开；后台队列、状态、取消、并发/输出/时间上限 | kernel benchmark 不是用户端延迟；不把讨论中的 5–10 秒作为保证 |
| 缓存污染或重复成本 | 物理缓存绑定快照、物理场景、代码与引擎版本；策略缓存绑定 ontology、objective、relation definitions、rubric、prompt/model/provider；缓存内容校验 | 托管模型权重版本未公开时明确 unreported，不能声称完全可重现；缓存不是新的真实模型调用 |
| 多插件本体所有权 | 共享类型归 Core；RoadFire 是当前唯一用例；变更由 CODEOWNERS/审查流程落实前以贡献规范管理 | 不提前复制 RoadRestriction 到多个插件命名空间，不提前实现尚不存在的扩展机制 |

## 版本与迁移规则

当前 ontology 为 `1.0.0`。当前手交包的 Scenario schema `1.0` 没有 ontology_version，读取该唯一已知 legacy 格式时采用 `1.0.0` 默认值，序列化输出始终写出版本。显式标为其他版本的数据必须拒绝，不可改字符串后当作迁移成功。旧开发运行的原始文件和哈希必须保留；增加版本字段后的场景需重新运行，不能把旧 run 绑定到新 overlay。

将来的破坏性迁移必须单独实现 `source_version → target_version` 转换，输出新副本和迁移记录（输入/输出哈希、代码版本、字段映射、丢失/不确定字段）；迁移 Scenario 和 ActionLog 后用新版本重放验证，旧导出继续可查看。不就地重写旧 ActionRecord、图、结果及验收证据。未实现的迁移路径应返回明确错误。

## 独立评价与校准

模型选择、术语和 rubric 在评估前冻结。由独立人工/领域专家给出语义相关性标签，区分训练、开发和保留评测集，记录标注协议、一致性和不确定标签。模型生成的“参考答案”不能代替独立标签。

有序相关性评分可报告排名相关性、绝对误差等；accuracy 需要预先定义类别和阈值。只有当输出与独立概率事件标签语义一致时，才计算 Brier/ECE，并记录分箱规则、样本量和置信区间。不能直接将归一化相关性用于事故风险的 Brier/ECE。目前这些校准结论为 **NOT_VALIDATED**。免费 demo 联通、typed 解析成功或 PPR residual 合格均不能替代校准。

## 结果与变更审查

结果页和导出分别提供 Physical、Graph、Semantic、Evidence；任何新增指标都必须说明单位、分母、时间范围、来源与缺失状态。`unreachable`、`unavailable` 和数值 0 不互换。设施受影响结论必须限定到被分析的起点和交通类别，不能从单个起点不可达推出全城医院隔离。

性能优化只依据同输入的测量；保持独立 routing oracle、dense/NetworkX PPR oracle、Action 重放和 typed projection 回归测试。新增缓存或近似求解器必须证明不会改变其宣称保持不变的物理结果/误差界。测试通过后停止重复审查，不以框架完整性为理由扩张 v1。
