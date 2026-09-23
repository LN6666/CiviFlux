# 05 · Qwen System-One：本地 Jev-style 决策层（Reflex 参考实现）

核查日期：2026-09-23。[S22–S24] 第一版不再依赖 closed Jev provider/Jev 注册、密钥、付费 API 或供应商可用性。UrbanImpact 自己定义 `QwenSystemOneBackend` 契约；第一版参考运行时采用 **Reflex + Qwen3.5-4B**，在部署者环境内本地推理。Reflex 是参考实现，不应成为核心算法的不可替换依赖。

## 为什么选这个实现

参考实现 `kshetrajna12/reflex` 是 MIT 许可的开源 Jev/System-One 重建，默认使用 `Qwen/Qwen3.5-4B`；Qwen3.5-4B 权重为 Apache-2.0。[S22][S23] Reflex 提供 `POST /v1/systemone`，输入 state + typed questions，输出 `noul / choice / score` 概率分布，不生成自由文本；README 明确说明可将原 Jev 客户端改 base URL 指向本地服务。[S22]

不要把另一个 `pngwn/system-one-qwen3.5-4b-scorer` 作为默认发布依赖：它很适合研究对照，但模型卡当前是 CC-BY-NC-4.0，且作者明确列出若干高基数/长上下文限制。[S24] 可以在研究消融中单独比较，不能无意把非商业限制带进主发行版。

## 参考运行形态

开发/发布参考服务器：

```bash
git clone https://github.com/kshetrajna12/reflex
cd reflex
git checkout <PINNED_COMMIT_OR_TAG>
uv sync
uv run reflex-serve --stable --port 8008
```

UrbanImpact 只调用：

```text
http://127.0.0.1:8008/v1/systemone
```

`stable` 是移动配置，**发布必须解析并记录精确 Reflex commit、Qwen model revision、precision/device、permutations 和 calibration file hash**，不能只记录 `stable`。首次下载 Qwen 权重需要网络；机构离线部署应预取/镜像权重，运行期不要求数据出网。

Reflex 当前文档对其发布用 4B 路径给出的参考是 **16 GB CUDA GPU**，并提供较小 0.8B WebGPU 演示；该演示明确不是发布质量替代品。[S22] 因此 UrbanImpact 的 release gate 以经过 UrbanRelationEval 的 Qwen System-One 实例为准，而不是以“能启动某个小模型”为准。若开发机没有合适 GPU，可把同一 `/v1/systemone` 服务部署在部署机构自己的 GPU 主机上；只要 endpoint 留在部署方环境、经过明确配置并记录 egress scope，仍符合 data-local 边界。


## 后端抽象与替换规则

核心代码只依赖 UrbanImpact 的 typed decision contract：`state + questions -> Choice/Score/Noul probabilities`。`ReflexBackend` 是 v1 的参考实现；不得把 Reflex 的内部 Python API 散落到 graph/ranking 代码。所有调用统一经过 `QwenSystemOneBackend.score_relations()`，这样未来可以替换为另一个 Qwen System-One 实现而不重写 KG/PPR。

发布默认 profile：

```text
backend_contract = qwen_system_one_v1
reference_server = reflex
model            = Qwen/Qwen3.5-4B
transport        = local/private HTTP /v1/systemone
free_text_output = forbidden
```

`pngwn/system-one-qwen3.5-4b-scorer` 可作为研究消融，但当前许可为 CC-BY-NC-4.0，不作为默认发行依赖。[S24]

## UrbanImpact 请求约束

本版继续使用 `Score` 给 relation type 的**任务相关性**评分，不让多个都相关的关系在一个 Choice 中被迫互斥。

```json
{
  "state": {
    "task": "urban_dependency_retrieval",
    "objective": "facility_access",
    "privacy": "abstract relation types only"
  },
  "questions": {
    "SEGMENT_USED_BY_ROUTE": {
      "type": "score",
      "instructions": "Assess semantic relevance of relation SEGMENT_USED_BY_ROUTE: a transit route uses this road segment. Do not infer delay or physical risk.",
      "criteria": ["Not relevant", "Indirectly relevant", "Directly relevant"]
    }
  }
}
```

UrbanImpact adapter 不依赖自由文本；逐问题验证 type、finite score、概率和≈1、score 与概率加权等级一致、legend 完整。服务端若返回额外 model/usage 字段可作为 provenance 保存，但 release 不能依赖供应商 token/billing 字段存在。

## 真正的数据流

`local Qwen System-One → checked scores → policy record → typed relation mixing → PPR → ranked entities → report provenance`

完成条件不是“本地服务返回 JSON”。必须：

1. 在多 relation fixture 上证明真实 Qwen 响应改变 transition matrix，且实际进入 PPR；
2. 在单 relation row 上验证统一缩放会被归一化抵消，不能伪造增益；
3. 在 Helsinki scenario graph 上消费真实本地响应并保存 transition hash；
4. 保存 pinned model/config/calibration provenance，而不是保存整张原始 KG；
5. A3 不必胜过 A2；如果没有增益，报告负结果，固定 PPR 仍可作为产品默认。

## 校准：必须按 UrbanImpact 自己的数据做

Reflex 自己强调温度校准应该针对部署工作负载拟合，模型/prompt/precision 变化后需要重做；它的通用 benchmark 不能替代城市域校准。[S22]

因此 WP6 增加 `UrbanRelationEval`：

- `calibration` 与 `test` 按 scenario family / corridor 分组，禁止同母题泄漏；
- calibration split 只用于 temperature fitting / threshold 选择；
- test split 冻结后不做 prompt 调参；
- 报告 accuracy/NDCG（如适用）、Brier、ECE、option-order sensitivity、重复运行稳定性；
- 小样本不宣传“已校准”，只报告观测值与样本量；
- v1 默认**不** LoRA 微调。只有独立证据表明 frozen 4B 在城市 relation task 不够且有足够训练数据时，才作为后续实验，不用 test set 反向训练。

## 数据本地化与安全

本地 System-One 是第一版的优势：默认不把城市数据发给 closed Jev provider、OpenAI、DeepSeek 或其他供应商。Web 插件不能直接把城市数据送到模型服务；调用发生在部署者的 UrbanImpact Core 内部。

默认请求仍只包含：event category、objective、relation definition、匿名/聚合上下文；**不发送 geometry、整张 KG、个人数据**。这样即使未来把 endpoint 放在机构内网另一台 GPU 主机，也保持最小披露。

若 `base_url` 不是 localhost，adapter 默认拒绝，部署者必须显式 `allow_remote_endpoint=true`；报告中标记 `data_egress_scope=organization_network` 或 `external`，不把“自托管”与“本机”混为一谈。

## 性能与成本账本

System-One 不再有按 token 付费 gate。记录的是：

- model bytes / first-load time；
- wall latency；
- questions/request；
- forward passes / permutations；
- GPU/CPU device、dtype、peak RSS/VRAM（能可靠测时）；
- calibration hash 和 cache hit；
- 模型下载是否已离线镜像。

不对每条 graph edge 调模型。优先给 relation types / small candidate context 批量评分，再交给 PPR 扩散。相同 `{model revision, calibration hash, objective, rubric, relation schema}` 的结果内容寻址缓存复用。

## 廉价 LLM 仍是独立层

DeepSeek、GPT-5.6 Luna 或其他廉价语言模型仍通过 `LanguageBackend` 可选接入，用于 scenario 草稿解析、歧义解释与最终文字说明。它们不是 Qwen System-One 的替代品，也不能修改路权、速度、OD、火灾范围或物理指标。远程 LLM 继续 BYOK、默认关闭；其数据出网与费用由部署者明确配置。

## 随包 smoke

先单独启动本地 Reflex/Qwen 服务，再运行：

```bash
python scripts/qwen_systemone_smoke.py
```

默认只允许 loopback。如果服务没启动，返回 `BLOCKED_ENVIRONMENT`，不会把 mock 当成通过；如果成功，它只证明 typed protocol 正常，不能代替 WP3 的真实 graph integration gate。
