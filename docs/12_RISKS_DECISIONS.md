# 12 · 风险与固定决策

| 风险 | v1处理 | 不允许的替代 |
|---|---|---|
| 没有历史GTFS/流量 | current-network what-if标记，历史数值NOT_VALIDATED | 当前feed假装历史 |
| 没有真实火灾警戒区 | 人工假设区明确记录 | 按severity捏造半径 |
| Qwen System-One本地模型/硬件不可用 | rules继续、local-Qwen gate blocked | mock说local模型完成 |
| Qwen System-One不带来增益 |保留真实backend，fixedPPR可作默认，发负结果 | 改标签/只留赢的案例 |
| 图只存道路没有语义 |必须跨road-route-facility关系与来源 |把OSM图改名KG |
| 大图/仿真慢 |CSR/cache/受控job/boundary测试 |先上集群/GPU |
| 数据少地区排名低 |coverage/unknown独立显示、必查设施不裁掉 |低置信度×0等于无影响 |
| 入图方向/层混乱 |ontology + direction fixture |全部无向PageRank |
| 稀疏type重权重不起作用 |测row normalization反例 |加噪声伪造Qwen System-One有用 |
| 用户以为消防响应可预测 |network travel time和实际response分开 |用速度×距离称response准确 |
| 机构服务器需求 |稳定API/executor seam/compose参考 |作者代运维账户系统 |
| 通用插件框架膨胀 |只一个插件、少量接口 |plugin商城/DSL语言先行 |

## 架构决策日志要求

每个重要改变写1页ADR：原决定、实测证据、替代方案、影响的schema/tests/消融可比性。不能以“未来扩展可能用到”为由加生产依赖。

## 增长路线（明确不是本轮）

后续Building Works可复用Restriction和external-effects contract；FDS/CFD、3D contextual enhancement、其他城市、NGSI-LD特定平台适配、multi-tenant、安全认证产品都不提前实现。当前v1完成是停止条件，而不是无限加新功能的起点。
