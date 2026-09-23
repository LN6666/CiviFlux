# ADR 0002 — 保留可验证的稀疏 PPR，按测量决定加速

状态：采用现有 CSR 实现，相关独立数值/投影检查已通过；完整发布验收仍由 `execution/STATE.md` 和必需 gates 决定。日期：2026-09-24。范围：GIS v1 的有向、加权、多关系 ontology projection。检查时本地依赖为 SciPy 1.18.1、NetworkX 3.7、NumPy 2.5.3；未新增依赖、本次算法评审未进行模型调用。生产 SimpleJev 付费调用按用户决定为 `DEFERRED_USER`；公开 demo 单列，普通生成式 Qwen 不替代该 classifier gate。

## 决定

生产继续使用确定性 SciPy CSR power iteration，明确全局 L1 residual、dangling redistribution、相同 baseline/event 条件和输入哈希。NetworkX PageRank 与小图 dense solve 保留为独立数值 oracle。先修正语义投影和 witness 搜索的正确性/扩展性，再根据同硬件、同输入 benchmark 决定是否添加 GraphBLAS 后端或单独的近似查询模式。

截至本次核查，NetworkX 3.7 的 PageRank 仍调用 SciPy sparse power iteration，支持 personalization、weighted directed graph 和 dangling vector。API 采用 `N * tol` 的停止规则；不能把它的默认 tolerance 当作本产品的固定全局误差阈值。[官方 API](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.link_analysis.pagerank_alg.pagerank.html)，[当前实现](https://networkx.org/documentation/stable/_modules/networkx/algorithms/link_analysis/pagerank_alg.html)。

## 比较

| 方案 | 当前问题的适配性 | v1 处理 |
|---|---|---|
| CSR power iteration | 直接处理现有稀疏 directed transition；输出全部节点，便于质量守恒、设施全集和成对 delta 检查 | 保留生产默认，记录实际 residual/iterations/mass error；排序与 node order 确定 |
| Approximate/local push | 稀疏 seed 与局部查询可能减少工作；近似 support、误差定义及归一化需单列，不能静默漏掉设施或把截断当精确 delta | 只有明确的局部查询性能需求、适用于本图的证明及独立误差验证后再引入 |
| GraphBLAS | 提供稀疏代数后端；NetworkX 列出 OpenMP GraphBLAS PageRank，已有 `graphblas-algorithms` 实现 | 保留后端 seam；先测 CSR 瓶颈、转换成本和数值一致性，再决定依赖 |

SciPy 官方列出 CSR 的高效行操作和矩阵向量乘法。GraphBLAS Algorithms 上游将其 NetworkX 后端标为 experimental；NetworkX 也提醒 graph conversion 和 cache 可能增加时间/内存开销。本项目尚未运行对照 benchmark，因此不声称换后端必然更快。[SciPy CSR](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csr_array.html)，[GraphBLAS Algorithms](https://github.com/python-graphblas/graphblas-algorithms)，[NetworkX backend 文档](https://networkx.org/documentation/stable/reference/backends.html)。

## “最新”算法的适用边界

2026-09-10 的预印本 *Accelerating the Local Push Primitive for PageRank Computation* 改进了 ACL local push 的理论复杂度，但其问题设定是 connected、unweighted、undirected simple graph，并调用 SDD solver；不是本项目有向加权关系图的直接替换。论文使用的 α 是 teleport/restart probability，本代码 α 是 continuation/damping probability，二者不能混用。[原论文 §1.1 与 §2](https://arxiv.org/html/2609.12076v1)。

较早的 EdgePush 专门讨论 weighted single-source PPR，通过 edge-level push 减少不均衡权重下的无效传播。这说明局部算法需要按工作负载和误差定义选择，不能仅凭发布日期决定。将其用于本项目仍需验证 directed/dangling、全设施结果和配对误差的具体处理。[VLDB 2022 作者稿](https://arxiv.org/abs/2203.07937)。

上述选择是本项目的工程判断：目前最值得优先解决的风险来自输入一致性和解释路径枚举，而不是已证实的 sparse matrix-vector 性能瓶颈。

## 必须保持的不变量

- 固定且唯一的节点顺序，合法 typed endpoints，经过注册的 projection ID 与 ontology version；graph payload/node-universe hashes 要重新计算核验。
- baseline/event 使用相同 snapshot、analysis time、objective、projection semantics、seeds、alpha、epsilon 和 relation policy。传入 scores 的 hash 必须与 spec 绑定；不同政策实验单列。
- directed current-connectivity 必须同时符合道路与 turn 的车种权限。static route alignment 和 candidate evidence 要明确标记，不能解释成当前可通行路径。
- 非负有限 transition/seed，seed mass > 0，non-dangling rows stochastic；有限 solver 参数；失败不能返回 `convergence=True`。
- 对 `F(x)=(1-α)s+α(Pᵀx+d(x)s)`，记录实际 `||F(x)-x||₁`。按 L1 contraction，可报告全局解误差上界 `residual/(1-α)`；不要把它与逐节点 normalized additive error 混淆。
- witness 搜索共用 adjacency/index，限制生成与排队数量；仅限制已访问路径数量不能限制内存。截断或未找到解释应明确记录，不能把 absence of witness 当作无影响。

增加后端时，用同一 frozen projection、seed、policy、dangling rule 和 residual target 比较时间/峰值内存及结果误差。新实现仍需通过 dense oracle、NetworkX oracle、无事件 delta=0、质量守恒和上述 review regression checks；不以 benchmark 好看为理由降低门槛。
