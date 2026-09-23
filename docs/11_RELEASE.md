# 11 · 发布闸门与“第一版全部正常运作”

## 必须gate

GATE-CONTRACTS：schema/OpenAPI/TS一致，时间/单位/有向道路转换完整。
GATE-NETWORK：独立router反例、城市限制/设施接入、不可达处理。
GATE-GRAPH：typed temporal KG真实构建，来源与ID审计，非空实际关系。
GATE-PPR：CSR/dense/NetworkX一致，delta可比较，Qwen System-One影响路径测试。
GATE-QWEN-SYSTEM-ONE：真实本地Qwen/Reflex HTTP成功、精确model+revision+device/dtype/permutations+calibration provenance、真实graph应用policy。mock/replay/skip不能通过；缺本地模型或硬件为BLOCKED_ENVIRONMENT。
GATE-SUMO：真实binary paired-run及hard closure/unfinished统计通过。
GATE-WEB：两个宿主、地图选取/进度/取消/解释/export闭环。
GATE-REAL-CITY：Helsinki真实bytes被下载、hash/许可/coverage和道路公告映射审计；fire事实/假设分离且真实地点情景运行。
GATE-ABLATION：A0–A5可复现，独立labels/无泄漏、负结果允许，成本/耗时表。
GATE-SECURITY：no secret/egress-off/安全输入/jobs隔离，安全限制显示。
GATE-REPRODUCE：clean checkout命令、lockfile、container固定、结果manifest可重放。

附加claim：`historical_numeric_prediction` 只有独立历史观测充分才能VERIFIED，缺失为NOT_VALIDATED，不与工程gate混淆。一般GIS v1完成可不具备此claim，但宣传不得隐去。

## evidence manifest

每gate字段status(PASS|FAIL|NOT_RUN|BLOCKED_ENVIRONMENT|BLOCKED_EXTERNAL)、producer、commit、commands[{command,exit_code}]、evidence_files[{path,sha256}]、executed_at、scope。PASS必须有真实证据文件。`check_release.py` 的结构层核对字段、状态和证据文件哈希；`make release-check` 还要求 PASS 的完整 Git commit 可解析、是当前 HEAD 的祖先，且该提交至 HEAD 的产品、测试、数据 fixture、依赖与构建输入未变，工作树内这些输入也没有未提交或未跟踪改动。文档与证据提交本身不会让相同代码的 PASS 失效。旧 CI 临时 merge commit 若不在当前 Git 历史中，不能仅凭 SHA 字符串沿用作当前 PASS。

上述校验是必要条件，不证明清单里自填的命令退出码对应真实运行，也不证明证据文件内容和验收范围正确。完成发布前仍须核对可信 CI/人工运行记录的 commit、日志、产物和 gate 范围；不能生成文字写“通过”代替日志。干净 Git 检出和足够的提交历史是当前修订校验的前提；浅检出缺少被引用的 commit 时会拒绝 PASS。

当前 `evidence/current_product_release.json` 中已有 PASS 是**所记旧提交及限定范围下当时的结果**。本轮代码、测试与构建输入已继续变化，旧证据不能自动升级为当前 HEAD 的 PASS；在相关受控输入上重跑并记录可信结果前，`make release-check` 应把它们列为 stale，同时继续列出未完成的生产模型、真实城市及消融 gate。不得为了消除 stale 而只改清单里的 commit、状态或 `engineering_complete`。

`evidence/product_release.json` 初始所有NOT_RUN；`scripts/check_release.py` 返回非零。WP7更新路径哈希并用CI独立运行。

## clean checkout使用体验

维护者提供 `make bootstrap`, `make demo-offline`, `make test-*`, `make release-check`。离线demo先有已构建image/deps和本地小数据包才能真正不出网；首次安装依赖需要网络要在README写清，不作绝对离线营销。

产品ZIP含配置、版本、操作录像/截图、报告而不是密钥/个人信息/整份新闻。city data只在许可允许时分发，否则附fetch manifest；GitHub不塞大城市原始文件。

## 最终release notes

“完成Road & Fire GIS v1；验证级别为[逐项]。Qwen System-One integration[真实/阻塞]。历史交通数值验证[有/无]。火灾为[外部限制情景/真实管制复现]。不可用于实时调度或安全撤离。”

没有成功真实本地 Qwen System-One inference 就不能写括号里“默认禁用但已经完成”；缺证据就发布pre-release/incomplete状态。不能让强大的UI掩盖未接上的引擎。


## Operational ontology gate

发布前必须：
- ontology manifest versioned并通过schema/codegen一致性；
- authoritative snapshot在scenario Action前后hash不变；
- Road/Fire修改只能由typed Actions进入overlay；
- ActionRecords可重放得到相同scenario hash；
- Object View能展示对象状态/links/facts/attention/evidence/actions；
- PPR使用显式ProjectionSpec；
- feature comparison matrix完成且source可追溯；
- 至少一个外部OSS邻居有真实reproduction note；失败也可接受，但不能伪造成功。
