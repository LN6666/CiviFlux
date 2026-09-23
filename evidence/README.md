# 验证证据索引

## 当前实现

- `current_product_release.json`：当前严格 release 状态，`make release-check` 读取此文件；未完成的必要 gate 使命令返回非零。
- `wp0/product_core_junit.xml`、`wp0/ontology_review.md`：产品/独立参考检查及本体审查。
- `wp1/`：Helsinki 来源、数据构建与候选事件映射。`case_review.json` 保留人工核验缺口。
- `wp2/`：实际路由与 PPR 场景运行摘要；`.runtime` 中的结果路径是本机证据，不假称已随 Git 分发。
- `wp3/`：SimpleJev 免费 typed API 原始响应、策略、provenance 与实际图应用；生产调用和校准仍未验收。
- `wp4/`：真实 SUMO 命令、输入、日志、输出、成功与失败记录。Junit 单列实际 simulator 检查。
- `wp5/`：两个 Web 宿主的真实浏览器检查、截图、导出包。测试强制禁用模型 API。
- `wp6/`：冻结场景、独立标签/oracle、消融、内核 benchmark、外部开源系统 smoke；`final_gate.json` 绑定代码与产物哈希。
- `wp7/`：最终检查、仓库卫生、干净检出和已安装 wheel 检查。离线缓存缺失的首次结果与后续安装验证分别保留。

## 原始工程包参考证据

本目录根部的 `product_release.json`、`PACK_TEST_REPORT.md`、`pack_status.json`、`reference-*`、`pack-audit.txt`、`qwen-systemone-smoke-blocked.txt` 等是**导入工程包的历史快照/测试 fixture**，不代表现在的产品状态。原始参考测试明确读取旧 fixture，因此不改写其数学 oracle 或“当时尚未实现”的输入样本来迎合当前实现；当前 release 状态使用单独文件。

`PASS_PROTOCOL_ONLY`、`PASS_LIVE_POLICY_GRAPH_ONLY`、`PASS_UNBLOCKED_ENGINEERING_SCOPE` 都是限定范围标签，不等于完整 v1。模型评分不是事件概率，当前数据不是历史真值，单个起点不可达不能推出全城设施隔离。
