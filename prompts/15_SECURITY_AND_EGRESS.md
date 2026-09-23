# SECURITY_AND_EGRESS

审核本地服务bind/session token/CORS、文件路径/ZIP/子进程/SSRF/XSS/日志redaction、取消和job隔离。离线测试拦截所有外部连接，含字体tiles和模型。Qwen System-One 默认仅连接部署者本地/内网 Reflex endpoint，不需要 BYOK；非loopback必须显式opt-in并记录egress scope。不得泄露原始graph或敏感设施信息。远程廉价LLM仍为BYOK且默认关闭。机构SSO/多用户归部署者，不因此省略软件安全底线，也不要趁机实现用户管理平台。
