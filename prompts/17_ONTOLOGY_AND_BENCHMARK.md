# Prompt · Operational Ontology + Competitive Benchmark Integration

读取 docs/14_OPERATIONAL_ONTOLOGY.md 和 docs/15_COMPETITIVE_BENCHMARK.md，并将其视为 v1 的规范性要求，不是未来愿望。

目标：在不扩大成通用 ontology platform 的前提下，把现有 Road & Fire GIS v1 从“KG + 算法”升级为 object/link/action/function 驱动的 operational ontology。

一次完成以下纵向闭环：

1. 建立 versioned ontology manifest，注册 v1 ObjectType / LinkType / Interface / ActionType / Function signatures；
2. 从 manifest 生成或一致性校验 Pydantic / JSON Schema / TS types，不维护分叉 schema；
3. authoritative city snapshot immutable；Scenario 通过 overlay + typed Actions 修改有效状态；
4. 实现 ActionRecord、precondition validation、atomic scenario workspace commit、replay hash；
5. LLM/System-One 不允许直接 CRUD graph；LLM只产生 action draft，Qwen只产生 soft semantic policy；
6. Operational Ontology 通过 ProjectionSpec 生成 PPR graph，审计/Run/Evidence 等对象默认不进入PPR；
7. Web Object View 展示 identity/state/links/facts/attention/evidence/actions/history；
8. 增加 T-ONTOLOGY 与 mutation tests；
9. 建立 comparison/feature_matrix.csv 和 benchmark manifest；只填有证据的 yes/no/partial/unknown；
10. 运行现有 A0–A5、工程性能 benchmark，并对至少一个可运行邻居项目写 reproduction notes；不做不公平总分排名。

硬边界：不复制 Palantir 专有代码/API，不依赖 Palantir，不做通用 ontology builder，不引入 Neo4j/RDF server作为v1硬依赖，不修改authoritative city data，不把PPR叫风险/因果，不把竞争项目 unknown 功能写成 no。

完成后更新 docs、contracts、work package evidence、release manifest；报告实际命令/exit code/artifact/hash。不要只写设计文档后宣布完成。
