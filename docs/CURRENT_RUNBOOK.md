# 当前运行手册

本手册描述当前产品代码。工作包状态和 release 闸门以 `execution/STATE.md` 与当次 `evidence/` 为准；原工程包的 `PACK_TEST_REPORT.md` 只证明来源参考检查。

## 1. 准备本地环境

在仓库根目录运行。Python 必须为 3.12；Web 使用 Node.js/npm。不要通过运行远程 shell 安装脚本绕过依赖管理。

```bash
uv sync --frozen
export PYTHONPATH="$PWD/core:$PWD"
```

然后在 `web/` 目录安装并构建前端：

```bash
npm ci
npm run build
```

`uv.lock` 与 `web/package-lock.json` 是依赖解析的依据。SUMO 的 Python wheel 包含本地 `sumo`/`netconvert`，当前 adapter 在启动时检查 **1.27.1**。首次安装依赖需要可达的软件源；已有本地缓存时可使用部署者自己的离线安装流程。运行城市分析不会自动下载模型或城市数据。

当前 macOS 环境可能忽略带隐藏属性的 editable `.pth`。开发时保留上述 `PYTHONPATH`，不需要关闭系统保护或更改安全设置。wheel 发布安装必须另做干净环境验证。

## 2. 启动产品

完成 Web build 后回到仓库根目录：

```bash
export PYTHONPATH="$PWD/core:$PWD"
uv run --frozen python -m api --port 8765
```

打开 `http://127.0.0.1:8765/`。参考地图宿主在 `/`，普通 HTML 宿主在 `/headless.html`。它们由同一个本地 API origin 提供；不要把生产集成改成未经审查的跨源开放 API。

服务默认只绑定 `127.0.0.1`。Web 客户端从 `/api/v1/session` 取得本进程随机 token，并通过 Bearer header 调用其余 API。token 不是 Qwen API key；不要把 Qwen key 填入浏览器。`CIVIFLUX_WORKSPACE` 可指定应用工作区，默认 `.runtime/app/`，其中包含 SQLite 工作区、jobs、cache 和 run artifacts。

典型流程：选择 citypack → 查看数据时期/缺失 → 创建道路或火灾情景 → 选择方向、时间、车种并确认假设 → Validate/commit Action → Run → 查看 baseline/event facts、attention 和 Object View → Export。取消按钮终止该任务，SUMO 取消会结束子进程树。

`A0/A1/A2/A5` 的本地计算不要求模型账号。`A3/A4` 所需的 System-One 服务为远程 SimpleJev Qwen classifier；生产付费调用已由用户暂缓，公开 demo 状态单列。界面必须显示该状态，不能用普通生成式 Qwen、rules 或 mock 顶替模型成功。

## 3. 运行产品检查

从仓库根目录、已设置 `PYTHONPATH` 的 shell 运行：

```bash
uv run --frozen python -m pytest -q test_suite/unit
uv run --frozen python -m pytest -q test_suite/sumo/test_sumo.py
```

Web 检查在 `web/` 运行 `npm run build` 和 `npm test`。实际 browser 测试需要可用的 Playwright 浏览器；缺少浏览器属于环境阻塞，不能记成 PASS。检查当前 Makefile 可用的工作包命令，常用入口包括 `make test-network`、`make test-sumo`、`make build-web`、`make test-browser`、`make demo-local`。

软件依赖清单由冻结锁文件离线生成。`make sbom-check` 对仓库保存的 CycloneDX、许可证文本及锁文件做跨平台一致性检查；`make sbom-host-check` 在当前机器的 `.runtime/sbom-host/` 重建并再次核查原生文件哈希。已保存的 macOS 原生文件清单不表示 Linux 二进制经过审查；Linux CI 会另生成本机清单作为运行产物。未知原生文件许可归属保留为待审，不能从父包许可证自动推断。

原工程包独立检查使用：

```bash
uv run --frozen python -m pytest -q tests
```

它们保留为独立参考，不替代产品 API、Web、SUMO 或真实 Qwen 的检查。每个 gate 分别记录 pass/fail/skip/blocked；release 所需测试被跳过仍会阻塞发布。

## 4. 真实 SUMO 示例

```bash
uv run --frozen python scripts/demo_sumo.py
uv run --frozen python scripts/demo_sumo.py --citypack data/citypacks/helsinki-current/citypack.json
```

第一条为手算可核查的合成双通道：关闭短路后改走长路。第二条从当前 Helsinki 数据选择一段有合法转弯的有向走廊及其局部备选边，施加明确假设封闭，使用 5 辆合成需求车辆。这是**有边界的代表性真实路网运行**，不是完整 Helsinki 事件回放、交通需求校准或城市预测验证。

每次运行生成新的 `evidence/wp4/synthetic-*` 或 `helsinki-*` 目录，不覆盖之前的原始证据。目录包含 `citypack.json`、`scenario.json`、`demand.json`、转换网络、共享 route input、闭路 XML、native 输出、命令日志和 `sumo_pair.json`。上级 `sumo_pair.json` / `helsinki_sumo_pair.json` 指向最新演示结果。

默认限额：300 simulation seconds、每个子进程 60 wallclock seconds、最多 1,000 vehicles、50 MB 输出、1-second step。Helsinki 演示使用 600 simulation seconds。请求被限制在 scenario window；teleport 禁用。真实输出报告 `arrived`、`unfinished`、`pending_departures`、`teleported`、`rejected_departures` 和到达车辆均值分母。关闭唯一通道的车辆等待/未完成，不能穿越封闭边，也不能当作零分钟到达。

Native 错误、碰撞、超时、取消或输出超限生成 `failure.json`，不生成成功配对文件。失败日志保留，不采用 `--ignore-route-errors` 掩盖无效路线。

## 5. Helsinki 数据

已有 citypack 时直接使用，不为同一验证重复下载。首次取得官方公共输入需明确出网：

```bash
uv run --frozen python scripts/data_pipeline.py fetch --allow-egress
uv run --frozen python scripts/data_pipeline.py build
uv run --frozen python scripts/data_pipeline.py review
```

数据源、文件哈希、下载时间、许可证、时间覆盖和缺失信息写入数据/evidence。compact reference 在 `data/citypacks/helsinki-current/`；正式当前网络案例的外圈包在 `data/citypacks/helsinki-boundary-outer/citypack.json`，属于部署者本地数据，不随公开仓库分发。不要硬编码 edge 数量或 citypack ID：裁切版本与原始 source hash 不同，须使用当次产物。

`evidence/wp1/road_scenario.json` 和 `fire_scenario.json` 是带证据标签的案例情景。设施入口未经核验、道路/公交 shape 几何关联、公告时间和假设限制不能升级为观察到的因果或历史交通真值。

`evidence/wp1/case_review.json` 当前标记 `human_review_status=PENDING`，公告地点到有向道路/事件位置的机器候选仍需独立人工复核；不能把机器生成的 review 页面当作人工已验收。设施全集表示所选 origin 与当前车种/时刻下的全部设施，不能据此宣称全市所有起点都可达或整座城市已经收敛。

扩大 Helsinki 当前路网边界的敏感性检查使用已冻结的 OSM 字节，不再次下载：

```bash
PYTHONPATH=core:. uv run --frozen python scripts/boundary_sensitivity.py
```

[实测报告](../evidence/wp2/helsinki_boundary_sensitivity.json)记录相同 origin、限制边与固定候选入口的三层路网比较。Road/Fire 各有 48 个可配对 OD：内圈→第一外圈分别有 3/8 个阶段差异；第一外圈→第二外圈各 96 个阶段在 1 秒阈值下均无差异，已配对路径也未改变，最大旅行时间变化分别为 0.612/0.814 秒。另有 3 个候选入口不能跨圈配对。独立转换仍改变大量共有边权重和转向，所以这只证明**这批 OD 在相邻外圈上的观测稳定性**，不证明全城收敛或历史预测准确。

已将第一外圈选为这 48 个候选目标的案例边界，并在它与第二外圈上通过真实产品 Action→路由→KG→固定 PPR 重跑 Road/Fire；执行 `PYTHONPATH=core:. uv run --frozen python scripts/formal_boundary_case.py`，核对[案例重放报告](../evidence/wp2/helsinki_formal_boundary_case.json)。原案例 51 个候选设施中另 3 个入口未能跨圈配对，2 个原生入口在扩大网络后会重新吸附；报告保留它们的未知状态。这个范围内的稳定性不能升级成全部设施、城市或历史事件有效性。

本地 API 启动时，若上述外圈包存在，只在它的 SHA-256 与正式案例报告相符且报告标明外圈范围已完成受限重放时，才在 `/api/v1/citypacks` 登记它；网页从下拉框直接选择，不通过 10 MiB 浏览器上传接口。外圈文件不存在时仍可使用 toy/compact 包，不自动下载；文件存在但与冻结报告冲突时启动失败，需核对本地数据而非默默回退。包级 warning 明示仅 48 个原候选入口的当前网络 what-if 稳定性，另 3 个未配对入口与 2 个重新吸附入口仍待核验；分析结果和导出 ZIP 的 `result.json` 也携带同一条范围说明及案例报告 SHA-256，而源 CityPack 的快照哈希保持不变。`CIVIFLUX_TOY_ONLY=1` 仅供明确的 toy/CI 运行；它不构成 Helsinki 产品验收。

历史事件回测须把来源事实、事发时路网/时刻、独立运营影响记录和独立数值观测分开验收；流程和指标见[回测协议](HISTORICAL_BACKTEST_PROTOCOL.md)。`python3 scripts/historical_backtest_preflight.py`只盘点当前证据，输出与[保存报告](../evidence/wp6/historical_backtest_preflight.json)可核对；它不会运行模型或把当前网络 what-if 评为历史预测。现有 R1 映射尚无人工接受，F1 实际警戒区未知，事发日期 GTFS 与独立实测目标均缺，历史数值结论继续 `NOT_VALIDATED`。

## 6. SimpleJev Qwen classifier 与暂缓的付费 gate

用户指定的服务是 **Featherless SimpleJev**，目标模型为 `featherless-ai/Qwen3.8-27B-classifier`。官方文档区分生产 `https://api.featherless.ai/v1/classifier` 与公开 demo `https://simple-jev-demo-api.featherless.ai/v1/classifier`；生产要求账号 key，demo 无需 key、受较小上下文与速率限制。可用模型应通过服务列表核验，不能仅凭配置名认定可用。[官方 API 文档](https://simple-jev.featherless.ai/docs)。

当前生产付费调用为 `DEFERRED_USER`。保持生产出网/预算关闭，不创建账号、不索取 key、不下载或启动本地模型。公开 demo 的授权、调用数、成功或服务错误单列；demo 成功不能冒充生产接入，也不能证明真实交通预测有效。配置与实际状态见 [adapter README](../adapters/system_one/README.md)。

SimpleJev 的 Score 是有序 rubric 的期望索引，Choice 为候选集条件概率，Noul 是转换后的评级判断；这些输出都不自动等同现实正确率。[服务语义](https://simple-jev.featherless.ai/docs)。普通 DashScope/Model Studio `qwen_api` 仅为可选比较，生成式 relevance、缓存 replay、rules 和 mock 均不能顶替 classifier gate。

无需新 API 请求即可重放冻结免费策略的关系分数负对照：`make policy-permutation-control`。它在合成图穷尽 720 种关系分数置换，保持城市、情景、物理 facts、seed 和 PPR 参数不变；[结果](../evidence/wp6/policy_permutation_control.json)只检验权重是否影响转移及其敏感性。事件图的单一关系权重会抵消；此检查不替代生产 A3/A4 消融或专家语义正确性验证。

恢复生产模型工作后，核验实际 endpoint、可用模型、typed schema、分数归一方式、配置/rubric provenance 和明确预算，再运行有界协议/图集成检查。只有批准的抽象 relation definitions 和 objective 可发出；城市对象、坐标、用户笔记、身份与物理参数留在本地。账号/服务链接目前仅供资料查询。

## 7. 定位故障

| 现象 | 检查与含义 |
|---|---|
| `ModuleNotFoundError: urbanimpact` | 从仓库根目录设置 `PYTHONPATH`；不要通过修改系统安全策略修复 |
| SUMO `BLOCKED_ENVIRONMENT` | 检查本地 binary 是否可执行及版本是否为 1.27.1；没有 binary 不能 skip 后发布 |
| `failure.json` / route error | 读同目录 native log、输入映射和 turn allowlist；不要打开全局 ignore-route-errors |
| `DEFERRED_USER` / remote endpoint unavailable | 继续本地核心；生产付费调用维持关闭，demo 状态单列，不以普通 Qwen key 或生成式 endpoint 顶替 classifier |
| 设施结果 `unavailable` | 入口未知；不能替换为最近道路中心然后声称核验接入 |
| 设施结果 `unreachable` | 当前方向、车种、时间、转弯规则下无路径；时间/距离必须为 null |
| Web 401/403 | 同源页面与当前 session token；服务重启后刷新页面，勿开放 CORS 绕过 |
| `not_stable` boundary comparison | 外圈改变关键 OD 结果；扩大范围或明确报告未稳定 |
| required check skipped | release gate 仍被阻塞，即便普通测试命令 exit 0 |

有新失败时记录 signature、假设、最小修复和受影响测试。相同失败至多三轮假设改变的修复；外部获取两次失败后记录并绕行。不要通过重复重装依赖、放宽 oracle 或无止境重新规划掩盖原因。

## 8. 导出与接续

完成的 run 可导出 result bundle，包含 scenario、ontology、action history、来源/投影/overlay hashes 和模型 provenance（如有）。原始数据、凭据和模型 key 不在导出包。保留对应 citypack 与 source hashes，才能在相同输入上复现。

新开发者先读 [DEVELOPMENT.md](../DEVELOPMENT.md)，再读 `execution/STATE.md` 的当前 checkpoint 与 evidence。不要重新执行已验证且输入不变的耗时下载或实验。发布前仍必须完成当前 release 闸门；没有测量数据时 `measured_prediction_validated` 保持 `NOT_VALIDATED`。
