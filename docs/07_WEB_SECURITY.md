# 07 · Web 插件与本地数据原则

## 两个真实宿主验收

1. MapLibre reference host：道路、设施、闭合区、before/after、时间轴、影响表、解释面板。
2. 独立vanilla HTML host：加载同一个构建产物、连接同一API，创建/查看/导出情景；MockMapAdapter测试生命周期。不得复制一份面板代码假装嵌入。

`<urban-impact-panel>`使用Shadow DOM样式隔离、键盘可达焦点/label、dispose解除订阅。只导出必要事件`scenario-change,run-complete,entity-select,error`；不要求宿主使用React。MapAdapter负责选中道路、渲染图层、高亮实体和fit extent；核心不要直接引用MapLibre对象。

## GIS UI验收

成功、空数据、不可达、缺历史feed、Qwen System-One禁用/失败/本地模型不可用、图未收敛、SUMO未完成、取消都有不同状态。结果卡区分`computed fact`、`simulation estimate`、`attention`、`assumed`。无模型依据的指标卡不显示0，而显示not available。

颜色只是辅助；图例带单位和范围。比较图使用相同色标/分母，不以两张独立自动色域夸大变化。table可回连map，导出保留所有限制/来源字段。没有在线底图也能用本地roads+districts完成演示。

## reference部署

一个由使用者启动的同源本地站点：`http://127.0.0.1:<port>`，前端 `/`，API `/api`，same-origin proxy。不是作者中心服务。机构可接自己的反向代理/认证；v1不建用户账号、RBAC、团队协作。

不要默认远程HTTPS页面直接fetch用户localhost；浏览器CORS/本地网络访问规则和证书需要特定宿主适配，非第一版默认方案。发包要说明：这是Web应用组件，不是浏览器扩展，不保证给任意在线城市网页注入按钮。

## 必须留在产品里的安全底线

绑定loopback、启动随机local session token（仅本机交付），no wildcard CORS+credentials；请求大小/文件数/ZIP展开比上限；路径canonicalization，阻止../、symlink逃逸；禁止XML外部实体和任意SQL/命令；用户提供的URL不直接变成SSRF代理；子进程参数数组，job workspace独立，cancel准确；渲染text而非任意HTML，防止source文档prompt injection影响权限；API key只在backend env，error也需redact。

离线模式测试拦截所有外部HTTP，包括tiles、字体、telemetry、model调用。导出默认剔除敏感原文和tokens。跨机构访问权限由部署方网关处理，说明未配置网关不得监听公网；这不是要求开发者代做机构IT。

## BYOK

默认off。用户显式开启Qwen System-One后由本地Core调用，前端显示使用的字段类别；不上传整张KG，不要求外部API。便宜LLM不能作为“错误自动修复者”操作服务器；只输出schema草案且经过同等校验。
