# 产品命令契约（当前实现；状态以实际退出码和证据为准）

用户指定的 System-One 是 Featherless 托管 SimpleJev Qwen classifier。下面的 API 预检只检查配置；生产付费调用仍未经授权。旧本地 Reflex/Qwen 说明见历史包，不属于当前验收路径。

| Target | 输出/失败语义 |
|---|---|
| make bootstrap | 根据锁文件安装，不静默升级；禁止echo成功替代安装 |
| make test-contracts / test-unit | 无网络、独立oracle，JUnit及实际exit code |
| make test-network / test-scenarios | 有向时空restriction与fire假设链 |
| make test-graph / test-ppr | ontology、lineage、数值残差、pair比较 |
| make systemone-preflight | 离线检查 SimpleJev 托管 API 配置、凭据、egress 和调用预算；未授权时 exit 2、`DEFERRED_USER`，不发请求 |
| make test-systemone-contract | 托管 SimpleJev typed wire/parser tests，不充当生产付费调用 |
| make test-systemone-local | 历史兼容 target：明确拒绝本地 Qwen 并 exit 2；不得用它替代 API 验收 |
| make citypack-fetch / citypack-build / test-data / case-review | 真bytes、manifest、日期与人工可审mapping |
| make test-sumo / demo-sumo-pair / test-cancel | 真binary，有日志和结果，缺binary不算通过 |
| make build-web / test-web / test-browser | 真browser+same component两host |
| make test-outcomes / ablate / benchmark / report | 原始指标、split、cost、negative findings |
| make clean-checkout-test / security-check / release-check | 全must gates，有任何required未运行则非0 |

make target 可以包装 uv/python/npm/docker，但不把 source 缺失或 live 跳过吞成 0。fast CI 可以有明确 nonrelease mock suite，release CI 不能因此变绿。免费 demo 的已冻结响应与生产 API gate 分开记录；生产调用继续为 `DEFERRED_USER`。
