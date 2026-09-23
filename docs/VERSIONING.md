# Git、版本与交接

- 仓库属于 `LN6666`；`main` 为已集成基线，开发分支使用 `codex/` 前缀（其他贡献者可使用 `feat/`、`fix/`）。通过 PR 展示变更、验证与本体/数据影响；`.github/CODEOWNERS` 指定当前维护者，成员加入时按模块更新。
- 使用独立主题提交：`feat(core)`、`feat(data)`、`feat(api)`、`test`、`docs`、`fix`。凭据、原始大数据、运行缓存及依赖目录不得提交；数据来源和 hash 必须保留。
- 应用包、Web 包当前为 `0.1.0` 开发版。只有 release manifest 所要求的 gate 全部满足才标记完整 v1。预览版本应明确标为 alpha；文档/单元测试通过不等于模型、历史场景或生产部署验收。
- ontology_version 独立于应用版本。破坏性契约改变必须有 ADR、迁移策略与旧输入拒绝/重放检查；不能只改版本号。详情见 `ARCHITECTURE_GUARDRAILS.md`。
- CI 固定依赖锁文件、GitHub Action commit 和 Ubuntu 24.04 runner，运行产品/参考/数据/真实 SUMO/浏览器检查。CI 不持有模型 Key，不触发 API 调用或城市数据下载。源数据获取、真实 provider 与容器环境分别记录。
- 验收证据记录实际代码 commit、命令退出状态及文件 SHA-256。生成报告后仅文档或证据提交可以使用其父代码 commit；改动实现后须重跑受影响检查。
- 交接必须更新 `execution/STATE.md`、`CHANGELOG.md` 和受影响 runbook；写明 blocker、可复现命令、证据位置及下一个必要步骤。保留失败证据，不能以新 PASS 文本覆盖未解决故障。
- 不改写已经共享的 Git 历史；修复用新提交。仅本地尚未共享的整理提交允许 amend。发布 tag 不移动，不在公开 issue/日志中粘贴凭据。
