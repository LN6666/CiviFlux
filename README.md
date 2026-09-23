# UrbanImpact · Road & Fire GIS v1 — Codex 工程执行包

版本：2026-09-23 / handoff-3-operational-ontology。项目名为工作名，未验证商标或包名可用性。

**本包是完整工程任务书、Codex 调度指令、数据证据登记和可执行参考测试；不是已经实现的城市插件。**
真实 Qwen System-One 请求、Helsinki 数据文件下载、SUMO 实际联调、浏览器产品验收需要在开发仓库执行；不能将随包的参考测试替代它们。

## 先做什么

1. 在新仓库根目录解压本包；已有代码时先保留现有工作、检查差异，不覆盖用户文件。根目录 `AGENTS.md` 是项目规则。
2. 将 `prompts/00_MASTER.md` 的内容交给 Codex。让它执行完整大工作包，而不是只复述方案。
3. 第一版的 System-One 不再依赖任何注册/付费 API：使用部署者本地的 **Qwen System-One backend**；第一版参考实现为 **Reflex + Qwen3.5-4B**。首次可从 Hugging Face 下载权重，正式离线部署应预取/镜像；运行时城市数据不需要出网。远程廉价 LLM 仍是可选 BYOK。
4. 按 `execution/work_packages.json` 推进 WP0–WP7；每个工作包一次交付完整纵向能力、测试、证据和可运行结果。`execution/goals.json` 是 54 项可核验目标，不是 54 次独立聊天。

## 第一版完成的定义

一个 **可嵌入 Web 的 GIS 插件**，可导入 Helsinki 路网/设施/公交数据，编辑道路限制和火灾外部影响情景，真实执行：

`Scenario → Routing / SUMO → typed temporal KG → fixed / Qwen-System-One-conditioned PPR → facts + attention + evidence → Web map / export`

固定规则、普通 PPR、Qwen-System-One-PPR 都必须存在；Qwen System-One 必须完成**真实本地 Qwen 模型推理**、进入真实投影计算并留下 model/config/calibration provenance；mock/replay 不能满足发布闸门。

**不做** QGIS 桌面插件、3D/BIM 平台、火灾 CFD、实际消防调度、个人风险画像、作者 SaaS、机构账号/协作/集群。机构自己承担服务器和运维。

## 文件导航

- `AGENTS.md`：短而强的不可越界规则。
- `docs/00_PRODUCT.md`：范围与最终验收。
- `docs/01_ARCHITECTURE.md`：模块、依赖、数据流、接口和 repo 布局。
- `docs/02_DATA_CASES.md`：Helsinki 真实事件与数据获取/分级验证。
- `docs/03_CONTRACTS.md`、`contracts/`：具体数据和 API 契约。
- `docs/04_KG_PPR.md`：图语义、PPR 数学、可比较性、防伪消融。
- `docs/05_QWEN_SYSTEM_ONE.md`：本地 Reflex/Qwen3.5 System-One 运行、校准、硬件、协议和真实联调。
- `docs/06_ROAD_FIRE_SUMO.md`：路网、消防事件边界和仿真陷阱。
- `docs/07_WEB_SECURITY.md`：Web 插件、数据本地化、安全与部署边界。
- `docs/08_TESTING.md`、`docs/09_VALIDATION_ABLATION.md`：代码、成果、真实事件、消融测试。
- `docs/10_EXECUTION.md`：大步推进、六个有停止条件的 loop、token 预算。
- `docs/11_RELEASE.md`：可执行发布闸门与证据要求。
- `docs/12_RISKS_DECISIONS.md`：技术决策与风险处置。
- `docs/13_JEV_TO_QWEN_MIGRATION.md`：从 closed Jev 依赖迁移到本地 Qwen System-One 的变更清单。
- `docs/14_OPERATIONAL_ONTOLOGY.md`：object/link/action/function 驱动的开放 operational ontology 规范。
- `docs/15_COMPETITIVE_BENCHMARK.md`：相邻项目、机构背景、产品差异和公平比较方案。
- `prompts/`：总指令、8 个工作包 prompt、恢复/诊断/审查/验证 prompt。
- `sources/registry.json`、`sources/SOURCES.md`：已核验来源与未核验数据，禁止重新发明出处。
- `cases/`：真实道路证据候选、真实地点火灾候选和合成最小反例；不是伪造的真实数据。
- `verification/`、`tests/`：本包自带的可运行独立 oracle、Qwen System-One 协议验证、发布闸门测试。
- `evidence/PACK_TEST_REPORT.md`：本次实际执行结果；与未来产品测试分开。
- `MASTER_PLAN.md`：合并阅读版，不建议每次把全部内容注入模型上下文。

## 本包参考测试（现在就可执行）

```bash
python -m pip install -r requirements-verification.txt
python -m pytest -q tests
python scripts/audit_pack.py
python scripts/check_release.py evidence/product_release.json
```

最后一条在当前状态**必须失败**：产品尚未实现，不能冒充 v1 完成。该脚本是状态+证据文件完整性门卫，不是代替人工/CI审查的真实性证明。

`make test-unit` 等产品命令是 WP0 必须创建的接口，不是声称本包已实现这些产品命令。参考测试使用 `python -m pytest tests`，与未来产品 `test_suite/` 分离。
