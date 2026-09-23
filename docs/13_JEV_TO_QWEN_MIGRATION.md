# 13 · Jev → Qwen System-One 迁移说明

核查日期：2026-09-23。[S22–S24]

## 为什么迁移

UrbanImpact GIS v1 不再把 TypeSafe Jev 的账号、注册、API key 或 hosted endpoint 作为任何发布前提。System-One 层改为部署方可本地/自托管的 **Qwen System-One**，参考实现为 `kshetrajna12/reflex` + `Qwen/Qwen3.5-4B`。[S22][S23]

## 哪些不变

- Road/Fire GIS、SUMO、typed temporal KG、PPR/Δ-PPR、Web plugin 范围不变。
- System-One 仍只做 soft semantic relevance，不触碰路权、速度、OD、火灾范围、物理指标。
- A0–A5 消融逻辑不变：A3 现在代表真实 Qwen-System-One-conditioned PPR。
- DeepSeek / GPT-5.6 Luna 等廉价 LLM 仍是可选 `LanguageBackend`，默认关闭、BYOK，用于场景草稿解析/歧义解释/文字说明。

## 哪些改变

1. `GATE-JEV/LIVE-PROVIDER` 全部替换为 `GATE-QWEN-SYSTEM-ONE`。
2. 不再检查 TypeSafe key/token/billing；改为检查本地/私网模型、revision、device/dtype、permutations、calibration hash 和真实 graph transition hash。
3. runtime 默认只允许 loopback；机构内网 GPU endpoint 需要显式 opt-in，并记录 egress scope。
4. 参考实现需要单独的模型运行环境；当前 Reflex 4B 发布路径文档指向 16 GB CUDA GPU。[S22] 缺 GPU 时允许继续所有非依赖工作，但 release gate 必须保持 `BLOCKED_ENVIRONMENT`，不能用 mock 或 rules 顶替。
5. 首次下载模型权重可需要联网；正式离线部署应预取并固定模型 revision。运行期不要求把城市数据发送给外部 AI。

## 为什么选 Reflex 作为参考而不是绑定它

Reflex 提供与 Jev 风格一致的 `POST /v1/systemone` typed contract，并明确支持 Choice/Score/Noul，不输出自由文本；其仓库 MIT，默认 Qwen3.5-4B 权重 Apache-2.0。[S22][S23] UrbanImpact 只依赖自己的 `QwenSystemOneBackend` 协议层，未来可换其他 Qwen System-One scorer。

另一个 `pngwn/system-one-qwen3.5-4b-scorer` 适合做研究对照，但当前模型卡为 CC-BY-NC-4.0，因此不作为主发行依赖。[S24]

## Codex 的迁移验收

必须证明：

- `make test-systemone-contract`：typed request/response fail-closed；
- `make test-systemone-local`：真实 Qwen 本地/私网模型推理，而非 mock；
- 多 relation fixture 中真实 Qwen score 改变 transition matrix；
- Helsinki scenario graph 消费真实 policy 并保存 `applied_transition_hash`；
- A2 vs A3 共用同一 physical facts，不能因为换模型重跑/篡改 SUMO；
- 校准/排序结果可以是负结果，A3 不要求胜过 A2；
- 无真实 inference 时发布状态必须是 `BLOCKED_ENVIRONMENT`。
