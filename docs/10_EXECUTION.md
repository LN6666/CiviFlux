# 10 · Codex 大步推进协议：8 工作包、54 goals、6 有界loops

## 大步的含义

一次交付完整能力而非一次写一个文件。每个WP包括contracts/实现/测试/运行样例/证据，默认直接从一个WP推进下一个可执行WP。不得“先研究几周，再逐个建空目录”。允许WP1数据核查与WP2算法工作并行，WP5前端在API契约冻结后并行。

依赖图见execution/work_packages.json。任务规模是工程分组，不是承诺某几周一定完成。

## 六个Loop

### L0 — bounded evidence acquisition
输入source registry；一次主入口+一次替代官方入口。每项至多两轮实质访问；失败记录HTTP/DNS/权限/日期覆盖，不换同义词无限搜。输出verified bytes或BLOCKED_SOURCE；能用current-network就明确标注，不编历史。

### L1 — large vertical implementation
读取active WP required docs→锁契约与验收→实现完整链→跑focused tests→生成demo artifact→更新STATE。只在module契约变动或WP边界跑全套昂贵测试。没有代码/测试产物的规划不算iteration成果。

### L2 — hypothesis-driven repair
每轮给出failure signature、具体因果假设、最小观测、patch、前后test输出。相同失败最多3轮，第三轮未解决转为缩小复现/独立review并明确阻塞下游；不得清空测试、放宽阈值、无限依赖重装。

### L3 — local Qwen System-One integration
先检查本地模型缓存/device/Reflex版本pin→启动本地 `/v1/systemone`→一次真实smoke→严格parse→真实图policy→保存model/config/calibration hash→cache replay。默认拒绝非loopback endpoint；模型不可达时继续rules/fixed-PPR目标，但全v1的Qwen gate保持 `BLOCKED_ENVIRONMENT`。不得把mock/replay当真实模型。

### L4 — ablation evaluation
固定data/split/facts→一次计算physical→A0–A5复用→独立评估→只在dev诊断→冻结→test最终一轮→报告正/负结果。相同输入policy cache复用，不循环让模型“优化回答”。

### L5 — integration/release
干净环境→build→fast→SUMO→browser→realcity→local-Qwen manifest→ablation→security/export→checksum→gate。证据缺失单独列，全部must gate PASS才engineering_complete；测量验证单独claim。

## 上下文与token纪律

初次读AGENTS+product+execution；之后只读activeWP和共享type diff。不要每一轮把MASTER_PLAN全文给模型。状态文件最多约150行，长日志在artifacts；失败报告截关键stack+repro，不贴几万行。

不做多模型“交叉投票”判断代码对不对。用test、oracle、mypy/tsc、浏览器测试。Reviewer只看验收指标、diff和失败证据，不让三个agents各自重新写完整方案。

至多3个实现worker并行，每个有不重叠的目录owner和返回格式；契约/lockfile只有integrator改。代码代理运行token按工具实际usage记账，无usage则unknown，不造精确数。项目System-One本地算力账本和Codex编程token账本分开。

## 每次handoff只写

`WP/GOAL状态 | 本次可运行产物 | 执行命令与退出码 | 失败/blocked根因 | 剩余budget | 下一个完整WP`。

缺少本地GPU/模型缓存/数据等环境信息只记录一次blocked，绝不在每步重复问城市/架构/是否3D。用户已选择Web、本地、Road&Fire、Qwen System-One+KG+PPR全v1，保持不变。

## 暂停规则不是半成品借口

本地模型/硬件或源数据阻塞时完成所有不依赖部分；精确列出剩余release gates。恢复后从STATE执行剩余门槛，不重写已经验证的模块。发现scope爆炸先删非v1能力，不删required本地Qwen System-One/graph/fire真实运行。
