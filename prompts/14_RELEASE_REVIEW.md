# RELEASE_REVIEW

从 clean checkout 执行全部 release 命令。任何 must test SKIP/MOCK/BLOCKED 均不算 PASS。按[当前用户决定](../execution/USER_DECISIONS.md)核查托管 SimpleJev 生产调用、准确的 provider/model 与客户端契约、预算和 provenance；服务未报告的权重 revision/校准不得伪造，免费 demo/replay 不替代生产 gate。另核查 Helsinki 数据 hash、SUMO 日志、双宿主浏览器 trace、消融 raw metrics 与安全检查。运行 `scripts/check_release.py`，但不把结构检查当证据真实性证明。分别给出 engineering complete 与 measured validation 状态；公开仓库推送已有用户授权，合并和发布仍遵守保护规则，不自动对公网部署服务。
