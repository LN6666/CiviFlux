# 03 · 契约：所有结果都能知道“依据什么”

当前 wire contract 以代码生成的 schema/Pydantic、[当前架构](CURRENT_ARCHITECTURE.md)及[用户决定](../execution/USER_DECISIONS.md)为准。原工程包中的本地 Qwen 字段属于历史设计，不能据此启动本地推理或把普通 chat 输出当作 SimpleJev。

JSON Schema 的初稿在 contracts/。它们是 wire-level 最低约束，生产 Pydantic 仍需做跨字段校验。必须从同一权威模型生成/一致性测试 TS types 与 OpenAPI，不能维护三个逐渐分叉的定义。

## Scenario v1

`schema_version, scenario_id, citypack_id, kind(road|fire), timezone, analysis_at, window, restrictions[], incident?, assumptions[], objective, engine, ranking, seed_spec`

restriction 必须有唯一 ID、**有向 edge IDs**、valid_from/to、blocked vehicle classes、evidence_ref、evidence_kind(observed|announced|assumed)。未知小时不可假装 observed；用 bounded uncertainty 字段和明确分析时刻假设。before/after window 为 UTC ISO8601，UI 用 Europe/Helsinki 显示。

fire.incident 的位置可为点或 geometry_ref；`fire_floor` 缺失允许，但设置 floor 不自动开启楼层传播。`perimeter_source=user|imported`，无默认火灾“等级→半径”映射。

## KG contracts

entity: `id, type, source_id, external_id, geometry_ref?, valid_from?, valid_to?, attributes`。
relation: `id, src, dst, relation_type, evidence_refs[], asserted_or_derived, derivation_id?, valid_from/to, confidence_status, base_strength`。

实体/关系 schema 必须列出合法 source/target 类型与传播方向。每个派生 `ROUTE_USES_SEGMENT` 或 `FACILITY_ACCESSED_VIA` 都保存路线/匹配的依据；仅 NEAR 不得被强制当成 SERVED_BY。

## Result fields：事实和注意力分开

每项 numeric metric 都带 `value, unit, definition_id, scope, evidence_level, uncertainty, numerator?, denominator?`。不可达用 `status=unreachable,value=null`；不要用 Infinity 进入 JSON，也不要默认为0。

rank record 含 `attention_score, delta_attention, rank_within_type, policy_hash, seed_hash, node_universe_hash, alpha, residual_l1, convergence, explanation_paths`。不提供 `risk_percent` 字段。

System-One policy record 除 scores 外保存实际 provider mode、模型 ID、客户端/请求契约、rubric、请求/响应哈希、usage 和 applied transition hash。托管服务未报告的服务器/权重 revision、device/dtype、permutations 与 calibration 只能记为未公开/未验证，不能填造本地 pin；token usage 只是调用诊断，不代表模型正确率。

`ResultBundle` 必须标明 `demand_kind=synthetic|estimated|measured`、`network_temporality`、`transit_temporality`、`simulation_status` 和实际 `provider_mode`。当前 SimpleJev 的 `simplejev_demo`/`simplejev_api`，以及 `replay`、`rules`、`mock_test`、可选普通 `qwen_api` 均不能互相冒充；旧 schema 兼容的 `local_qwen`/`remote_reflex` 不满足当前 release gate。前端不能去掉这些标签。

## 本地 API（WP0 创建并保持稳定）

- `GET /v1/health`：版本和依赖能力；不泄露API key是否具体是什么。
- `GET /v1/capabilities`：数据/引擎/Qwen System-One模式，缺失功能原因。
- `POST /v1/citypacks/import`：仅上传/已授权本地路径，不是任意远程URL下载代理。
- `POST /v1/scenarios/validate`：语法、空间、时间、数据覆盖、事实/假设报告。
- `POST /v1/runs`：创建 job，202、run_id、status_url；幂等键绑定规范化输入。
- `GET /v1/runs/{id}`：queued/running/completed/failed/cancelled，stage进度，不能虚报0–100。
- `POST /v1/runs/{id}/cancel`：终止子进程树，原子标记，不删除别人的文件。
- `GET /v1/runs/{id}/results`：JSON摘要+本地artifact引用。
- `GET /v1/runs/{id}/export`：ZIP，来源、assumptions、metrics、graph、rank、manifest。

轮询足够；不强制 websocket、消息队列。错误结构统一 `code,message,stage,retryable,details_redacted`。reference服务只认部署方local token，同源proxy；多人身份在边界外。

## 外部调用边界

下载源只由本机配置登记；模型只接受脱敏relation描述和objective。任何申请权限、改变限行、改变baseline的数据变更必须 deterministic 校验+用户确认。LLM解释不能改ResultBundle。


## Operational Ontology contracts

`contracts/ontology_manifest.schema.json` 与 `contracts/action_record.schema.json` 是新的最低 wire-level 契约；完整语义在 `docs/14_OPERATIONAL_ONTOLOGY.md`。生产实现必须从单一 ontology manifest 生成或一致性校验 Pydantic/TS/JSON Schema。

- authoritative object 不可被 scenario Action 覆写；
- restriction/fire incident 是 scenario objects，不是 RoadSegment 的裸字段 patch；
- Action 先验证 preconditions，再原子提交 overlay；失败不允许 partial commit；
- LLM 只能返回 Action draft；同一 validator 负责用户/UI/LLM 来源；
- ResultBundle 新增 `ontology_version, scenario_overlay_hash, action_log_hash, projection_id, projection_hash`；
- export ZIP 必须包含 ontology manifest version 与 ActionRecords。

本地 API 在实现时增加：
- `GET /v1/ontology`：类型/能力摘要，不返回城市数据；
- `POST /v1/actions/validate`：typed Action preflight；
- `POST /v1/actions`：提交 scenario Action；
- `GET /v1/scenarios/{id}/actions`：场景操作日志；
- `GET /v1/objects/{id}`：Object View 所需 identity/state/links/facts/evidence/actions 摘要。
