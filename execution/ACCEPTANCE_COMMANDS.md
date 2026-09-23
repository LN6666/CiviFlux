# 产品命令契约（WP0建立，不是本包已实现）

| Target | 输出/失败语义 |
|---|---|
| make bootstrap | 根据锁文件安装，不静默升级；禁止echo成功替代安装 |
| make test-contracts / test-unit | 无网络、独立oracle，JUnit及实际exit code |
| make test-network / test-scenarios | 有向时空restriction与fire假设链 |
| make test-graph / test-ppr | ontology、lineage、数值残差、pair比较 |
| make systemone-preflight | 检查本地Reflex/Qwen服务、模型pin、hardware、calibration；缺失exit2并给BLOCKED_ENVIRONMENT |
| make test-systemone-contract | typed wire/mock parser tests，不充当真实模型 |
| make test-systemone-local | 真实本地Qwen System-One→真实graph；缺模型/硬件/服务exit2且阻塞full release |
| make citypack-fetch / citypack-build / test-data / case-review | 真bytes、manifest、日期与人工可审mapping |
| make test-sumo / demo-sumo-pair / test-cancel | 真binary，有日志和结果，缺binary不算通过 |
| make build-web / test-web / test-browser | 真browser+same component两host |
| make test-outcomes / ablate / benchmark / report | 原始指标、split、cost、negative findings |
| make clean-checkout-test / security-check / release-check | 全must gates，有任何required未运行则非0 |

make target可以包装uv/python/npm/docker，但不把source缺失或live跳过吞成0。fast CI可以有明确nonrelease mock suite，release CI不能因此变绿。
