# CiviFlux — Road & Fire GIS

CiviFlux 是部署者本地运行的道路限制与火灾**外部交通影响**分析工具。Python 分析内核提供有向路由、真实 SUMO 配对仿真、typed operational ontology 和确定性 PPR；Web Component 通过本地 HTTP API 嵌入地图或普通网页。

当前仓库已经包含产品实现、真实 Helsinki 数据构建和 SUMO 运行证据。**是否达到完整 v1，以 `execution/STATE.md`、当次测试日志和 release evidence 为准。** 随工程包附带的参考测试通过，不等于产品或真实 Qwen 集成通过。

当前用户指定的模型方案是 **Featherless SimpleJev 的 Qwen classifier**，通过远程 typed API 使用；不在本地部署或下载模型。普通 DashScope/Model Studio 生成式 Qwen API 仅保留为可选比较，不能替代该 classifier。生产付费调用按用户决定为 `DEFERRED_USER`；公开 demo 的检查单独记录，不冒充生产验证。详见 [模型 adapter 状态](adapters/system_one/README.md) 与 [运行手册](docs/CURRENT_RUNBOOK.md)。

## 从这里开始

- [文档导航与用户决定](docs/index.md)：当前实现、迁移覆盖关系与历史来源入口。
- [Codex 轮替交接](docs/CODEX_HANDOFF.md)：其他人或其他账户接手时的读取顺序、未完成目标、账号与费用边界。
- [当前运行手册](docs/CURRENT_RUNBOOK.md)：环境、测试、真实 SUMO、数据、Qwen 和故障处理。
- [当前实现架构](docs/CURRENT_ARCHITECTURE.md)：模块职责、数据流、扩展位置和结果语义。
- [工程决策](docs/adr/0001-current-architecture.md)：不可变城市快照、Action overlay、成对计算与 API 边界。
- [贡献约定](CONTRIBUTING.md)：文件归属、验证与可复现交付。
- [变更记录](CHANGELOG.md)：当前实现与来源工程包的区别。

## 本地验证

需要 Python 3.12、`uv` 和 Node.js。`uv.lock` 与 `web/package-lock.json` 固定本地依赖。SUMO 由 Python 依赖提供，adapter 要求实际 binary 为 **1.27.1**。

```bash
uv sync --frozen
export PYTHONPATH="$PWD/core:$PWD"
uv run --frozen python -m pytest -q test_suite/unit/test_network.py
uv run --frozen python -m pytest -q test_suite/sumo/test_sumo.py
uv run --frozen python scripts/demo_sumo.py
```

最后一条实际启动本地 `netconvert` 和 `sumo`，将配对结果、命令、日志、输入和哈希写入 `evidence/wp4/`。它使用明确标注的合成双通道网络；无模型、无 API 费用，不触发城市数据下载。

本仓库的 Python 开发命令显式设置 `PYTHONPATH`。在当前 macOS 环境，隐藏属性的 editable `.pth` 文件可能被 Python 启动逻辑跳过；无需修改系统安全设置。发布安装应使用构建的 wheel，并独立验证干净环境。

## 目录

| 路径 | 职责 |
|---|---|
| `core/urbanimpact/` | 契约、immutable snapshot、Actions、路由、graph projection、PPR、analysis use case |
| `api/` | 本地服务、token、任务/取消、对象查看与导出 |
| `web/` | Web Component、MapAdapter、MapLibre 参考宿主和普通 HTML 宿主 |
| `adapters/` | OSM、GTFS、SUMO、SimpleJev/可选生成式 Qwen 的边界适配 |
| `ontology/` | 对象、关系、接口、Action 的版本化注册表 |
| `test_suite/` | 当前产品测试，真实 SUMO/browser/API gates 分开报告 |
| `tests/`, `verification/` | 原工程包独立参考检查，保留且不冒充产品 |
| `data/`, `evidence/` | 本地输入、来源日期/哈希、真实运行记录；大文件是否纳入分发由发布流程决定 |
| `execution/` | 当前 checkpoint、工作包、目标和 release 状态 |

## 解释结果

- 路由输出是固定权重下的距离、网络行程时间和可达性；没有路径时为 `null` / `unreachable`，入口未知时为 `unavailable`。
- SUMO 默认 `SYNTHETIC_DEMAND_WHATIF`。报告包含全部需求分母、到达、未完成、teleport 和 rejected departures；只对到达车辆求均值时明确说明分母。
- PPR 是关联注意力，不是风险、因果、撤离安全或应急响应预测。Qwen 只能调整软语义相关性。
- 当前 OSM/GTFS 不构成历史事故当天真值。公告事实、人工映射、假设封路和测量验证分别标记。
- Helsinki 来源公告到有向道路的映射仍待独立人工复核（`evidence/wp1/case_review.json`）；机器候选不构成已验收案例。选定 origin 到全部设施的检查也不等于全市所有起点的可达性保证。
- 火灾边界由用户确认或导入。系统不从“严重程度”生成消防半径，也不自动放宽应急车辆权限。

## 当前文档与来源方案

`docs/00_PRODUCT.md`–`docs/15_COMPETITIVE_BENCHMARK.md`、`prompts/`、`MASTER_PLAN.md` 保留工程包的验收来源。它们包含原始的“必须本地 Reflex + Qwen”文字；本地部署选择已由当前用户的 **远程 SimpleJev classifier、生产付费调用暂缓** 决定替代。当前 typed contract 以 SimpleJev adapter 和已核对文档为准；普通生成式 Qwen API 不能顶替。模型真实性、预算、证据和物理结果隔离等要求继续适用。

阅读顺序为：本 README → 当前运行手册/架构 → `execution/STATE.md` → 当前工作包需要的来源文档。原始 README 保存在 [HANDOFF_README.md](docs/HANDOFF_README.md)。不要从旧计划中的 `NOT_IMPLEMENTED` 或旧模型 gate 推断当前运行状态，也不要把当前工程完成误写成历史交通预测已验证。

项目不提供作者代运营 SaaS，也不承担市政账号、SSO、HA、备份或应急指挥。用户已授权将本仓库公开发布到 `LN6666/CiviFlux`；这不包含付费 API、对外发消息或完整 v1 release 授权。
