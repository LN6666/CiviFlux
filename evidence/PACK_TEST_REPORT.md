# 本次实际执行的参考测试报告

生成时间：2026-09-23T13:49:48.289423+00:00。执行范围：**handoff 独立 reference checks**，不是未来 UrbanImpact 产品。

## 本次迁移结论

- hosted Jev / TypeSafe 注册、API key、token 计费已从 GIS v1 的必需依赖中移除。
- v1 System-One 改为 `QwenSystemOneBackend`；参考运行时为本地/私网 **Reflex + Qwen3.5-4B**。
- 当前 handoff 容器没有 Reflex/Qwen 服务，因此真实本地模型 gate 被正确标记为 `BLOCKED_ENVIRONMENT`，没有用 mock 冒充通过。
- DeepSeek / GPT-5.6 Luna 等廉价 LLM 仍是可选 `LanguageBackend`，不属于 v1 release 必需 gate。

## handoff-3 Operational Ontology 更新

- 新增 `docs/14_OPERATIONAL_ONTOLOGY.md`：Object/Link/Interface/Action/Function/Projection 规范；Palantir 仅作为公开架构思想参考，不成为依赖。
- 新增 `docs/15_COMPETITIVE_BENCHMARK.md`：EU Urban Flow、TWA、CReDo、TUM rescuePY、NYU/FDNY、SUMO_LLM_Agent、FireCom 的机构背景、功能差异和公平比较方法。
- 工程目标由 48 增为 **54**；新增 ontology/action/projection/object-view/competitor-benchmark/release-audit 六个硬验收目标。
- 新增 `ontology_manifest.schema.json` 与 `action_record.schema.json`；pack audit 会验证这些 JSON Schemas。
- 当前 reference tests 仍为 **66 passed**；它们验证 handoff 参考实现和协议，不代表产品 ontology/runtime 已开发完成。

## 已实际执行

| 命令 | 结果 | 证据 |
|---|---|---|
| `python -m pytest -q tests --junitxml=evidence/reference-junit.xml` | **66 passed**，exit 0 | `reference-pytest.txt` / `reference-junit.xml` |
| `python scripts/audit_pack.py` | **8 work packages / 54 goals / 39 sources，PASS** | `pack-audit.txt` |
| `python scripts/run_reference_demo.py` | 合成小图 routing + typed policy → transition → PPR，exit 0 | `reference_outcomes.json` / `reference-demo.txt` |
| `qwen_systemone_smoke.py` 指向未监听 loopback 端口 | **预期 BLOCKED_ENVIRONMENT，exit 2**；不会访问外部 AI | `qwen-systemone-smoke-blocked.txt` |
| `python scripts/check_release.py evidence/product_release.json` | **预期 exit 1**；产品 gates 尚未执行 | `product-release-gate.txt` |

## 参考成果，不是真实城市预测

固定 toy 路网 A→H 基线成本 **3 秒**；封 `bc` 后 **7 秒**；封唯一末端 `ch` 后为**不可达/null**。这些秒数只是自定义测试权重，不是 Helsinki 行程时间。

typed mock policy 改变后 PPR 向量 L1 差 **0.268018018018**，证明 policy 确实进入 transition/ranking 代码。该 policy 明确是测试 mock，不能证明 Qwen System-One 本身有效。

power iteration 与独立线性方程 oracle 最大绝对差约 **2.406e-13**；residual L1 约 **8.899e-13**。测试同时验证：同一节点全部出边统一缩放会被 row normalization 抵消，因此不能把“调用了模型”冒充成“模型改变了排名”。

## 当前没有完成

没有完整生产插件、真实 Helsinki citypack bytes、SUMO 实城 paired run、浏览器 E2E、真实 Qwen System-One graph integration、独立历史 traffic outcome 数值验证。

Reflex 当前文档的发布用 4B 路径面向 CUDA GPU；本 handoff 环境没有对应模型服务，因此 release gate 必须保持未完成。正式开发应在部署者本地或私网 GPU 主机跑真实 inference，保存 Reflex commit、Qwen revision、device/dtype、permutations、calibration hash 和 applied transition hash。

这是工程执行包的已测参考基线，不是全插件完成声明。
