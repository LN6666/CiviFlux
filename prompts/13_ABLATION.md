# ABLATION

冻结data/splits/physical facts，确认A0–A5唯一差异来自声明模块。先跑廉价oracle筛bug，再在相同情景执行A0/A1/A2/A3/A4/A5。A3用真实Qwen System-One政策记录，缓存复用，禁止按edge重复请求。只在dev调整有限参数；test不做prompt寻优。报告所有变体原始数据、成本/耗时/coverage与负结果。若Qwen System-One无效检查row归一化是否取消类型权重；正确取消应报告，不得注入噪声。
