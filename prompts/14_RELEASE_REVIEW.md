# RELEASE_REVIEW

从clean checkout执行全部release命令。任何must test SKIP/MOCK/BLOCKED均不算PASS。核查真实本地Qwen System-One model/config/calibration manifest、Helsinki数据hash、SUMO日志、双宿主浏览器trace、消融raw metrics与安全检查。运行scripts/check_release.py，但不把结构检查当证据真实性证明。给出engineering complete及measured validation各自状态；不自动push或部署公网。
