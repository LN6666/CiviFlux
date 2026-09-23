# 开发接续

先看 `README.md` 和 `docs/CURRENT_RUNBOOK.md`，然后看 `execution/STATE.md` 的当前 checkpoint、阻塞与 evidence 路径。`git status` 是判断已有工作和文件归属的依据。不要把来源工程包的旧状态覆盖回当前实现。

## 一次接续的顺序

1. 确认当前目标、已接受决策和要交付的可运行结果。当前 System-One 目标为 Featherless SimpleJev 的远程 Qwen classifier；普通生成式 Qwen 仅为可选比较，不启动本地模型/GPU下载工作，生产付费调用 `DEFERRED_USER`，公开 demo 证据单列。
2. 读取当前包必须的契约/文档，找到对应 `core/`、`api/`、`web/`、`adapters/` 与 `test_suite/` 实现。
3. 修改后运行受影响的 focused checks。到工作包边界运行完整 gate，保存真实命令、exit、scope、hash 与失败/阻塞。
4. 更新短 STATE，并链接长日志。已验证且输入不变的证据可以复用。不要为了多一轮检查重复下载、付费调用或改动冻结科学结果。

## 文件归属

| 领域 | 负责范围 | 协调点 |
|---|---|---|
| Integrator | shared contracts、ontology、pipeline/API、lockfiles、Makefile、release evidence | 对外稳定接口和全套 gate |
| Data | OSM/GTFS/citypack、source/case evidence | stable IDs、时期、geometry/turn/classes |
| Network/simulation | router、restriction compiler、SUMO adapter/fixtures | OD/result fields、native limits、完整需求分母 |
| Graph/provider | projection、PPR、SimpleJev/可选 Qwen、消融/evaluation | policy semantics、相同 paired inputs、真实调用 provenance |
| Web | component、map adapters、两宿主、browser tests | TypeScript wire contracts、Action API、Object View |

并行开发前明确互不重叠的具体文件；此表不是允许任意覆盖别人工作。契约与 lockfile 由一个 integrator 统一修改。

## 重要实现入口

- `core/urbanimpact/pipeline.py::AnalysisService.run`：物理 facts、projection、ranking 和 result 组合。
- `core/urbanimpact/actions.py::Workspace`：Action validate/commit/replay，不可变 city snapshot。
- `core/urbanimpact/network.py::Router.compare`：全部设施的 baseline/event OD facts。
- `adapters/sumo/adapter.py::SumoAdapter.run_pair`：真实本地 paired simulation，目录必须为空以保留历史 evidence。
- `adapters/system_one/`：SimpleJev typed contract、远程 classifier endpoint、可选生成式 Qwen 比较及预算/egress/provenance 边界。
- `api/services.py::RunService`：job state、取消、export、Object View。
- `web/src/map-adapter.ts::MapAdapter`：宿主地图集成 seam。

物理核心测试中的原始反例/独立 oracle 不可删除。Mock/provider contract tests、真实 SUMO、浏览器和 live Qwen 必须分别报告。生产付费模型调用按用户决定为 `DEFERRED_USER`；不要再次索取 key 或预算；公开 demo 与生产证据分别标记。缺少浏览器或 binary 是具体 blocker；不能通过改变 mode、skip 或放宽阈值把它变成 PASS。

完整贡献规则见 [CONTRIBUTING](CONTRIBUTING.md)，架构理由见 [ADR](docs/adr/0001-current-architecture.md)。
