# 00 · 产品边界与最终可交付物

## 不是研究选题，而是一个完整工程产品

交付一个 Road & Fire GIS Web 插件。用户在宿主地图选道路、绘制限制区、指定事件时间和交通类别，运行情景，看到可追溯的道路/公交/设施影响及关系解释。首个宿主是自带的 MapLibre 参考 Web App；第二个宿主是无地图的 vanilla-HTML 控件集成测试，用来证明不是只能运行在自己大屏里的单体应用。

不要求第一版与所有 EU 数字孪生平台直接安装兼容。没有统一的“欧洲城市插件商店协议”。输出稳定的 Web Component、MapAdapter、HTTP API，将具体平台 SDK 集成留给后续适配器。

## 用户一次完整操作必须包括

打开本地部署 → 导入/选择已登记 citypack → 浏览数据日期/范围/缺失 → 选择道路限制或火灾事件 → 指定受限对象/时间/车种并确认假设 → 验证情景 → 运行 → 显示进度与取消 → 展示 baseline/event → 切换 A0/A2/A3 分析模式 → 选一个设施查看路由/图路径/来源 → 导出可复现结果包。

火灾场景不得因为没有三维楼体而失效；可以使用事件点/建筑轮廓。但没有楼层数据不得声称分析三楼与四楼的传播差异。无警戒区信息时，不自动产生所谓正确警戒半径；让用户明确输入“情景假设”。

## v1 必须有的五组结果

1. **道路与路由事实**：车种/方向/时段受限，绕行距离和固定权重网络行程时间差，不可达/未完成单独统计。
2. **SUMO 情景结果**：相同 demand、seed 下 before/after 行程时间、未到达数、队列/路段速度（有输出才展示）。默认 synthetic demand 必须有醒目标记。
3. **公交与设施关联**：公交路线潜在受影响、设施接入变化；没有可靠公交道路匹配只能显示 candidate，不是取消或延误实测。
4. **图注意力**：typed KG、固定 PPR、Qwen-System-One-PPR、条件相同的 delta-PPR；不把小数标为风险百分比。
5. **证据与重放**：数据版本、假设、模型版本、Qwen System-One provenance、关系来源、图大小/截断、指标单位、缺失信息、消融报告。

## 完成 != 所有城市预测都准

`engineering_complete` 要求所有必须功能和真实集成跑通。
`source_replay_verified` 只覆盖已核验公告/人工映射事实。
`measured_prediction_validated` 需要独立、同一时期的真实观测；缺失就为 NOT_VALIDATED。

可以发布明确标注边界的 GIS v1，但不得将没有测量证据的产品宣传为实战交通/火灾预测器。不能用“调通 API”替代“模型判断有增益”，也不能因为没有增益就伪造漂亮消融结果。

## 本版不做

账户/组织管理、SaaS、中心数据托管、多人编辑冲突、城市内网部署代运维；3D Tiles/CityGML/BIM 核心依赖；FDS/CFAST/火焰和烟羽预测；实际消防派车、真实应急路线推荐、安全撤离指令；装修/洪水/全套活动插件；训练 GNN 或新基础模型；多城市大规模同步；实时 HFP 永久在线订阅；通用自然语言自主操作平台。

## release acceptance

全部必须闸门参见 docs/11_RELEASE.md；缺少真实 Qwen System-One 或真实 citypack 测试就不能称“第一版全部正常运作”。提供缺口状态，不通过编造或 mock 消除缺口。


## v1 的产品差异：Operational Ontology

Road/Fire 并非直接 patch GIS 图层：道路、设施、事件、restriction、scenario、run、evidence 与 impact observation 使用 versioned typed objects/links；用户操作通过 typed Actions 写入 scenario overlay，authoritative city snapshot immutable。Web Object View围绕对象展示事实、links、attention、证据和允许的actions。详见 docs/14_OPERATIONAL_ONTOLOGY.md。
