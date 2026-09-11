# 仓库层最终状态 / Repository freeze

本轮仅冻结仓库结构与实现范围，不代表生产部署或完整 AGT 编译验收。后续优先通过真实 E2E 暴露问题，不继续增加安装器、daemon、GUI 或其他抽象。

## 状态表

| 范围 | 状态 | 证据层级 / 边界 |
|---|---|---|
| AGT 4.7.0 官方 baseline、缺文件语义、/dev/null | PASS | 静态官方源码比对 + 本地真实补丁操作；commit 85fb4fe688997d3a0c2930b7a202cf22f617b092 |
| dry-run/apply/repeat/rollback 删除新增文件、unknown/partial 拒绝 | PASS | 本地 executable tests，临时源码目录，非生产源码 |
| OAuth evidence_files | PASS | 官方原始 oauth.rs LF hash；目标目录 evidence 缺失/变化拒绝，无 Git HEAD 要求，不改 evidence |
| preferred B / active A，fallback 更新 key，legacy enterprise 防误锁 | PASS | 提取真实 ProxyToken、refresh 方法、上游候选排序/fallback；HTTP/config mock，真实 DashMap + 本地原子持久化 |
| rotation、五个 token 字段、oauth_client_key、未知字段保留 | PASS | 本地 Rust executable；真实代码提取，合成账号数据；不等于真实 Google rotation |
| 原子替换、失败清理 | PASS | Windows 原生 MoveFileExW 路径及共享锁拒绝替换测试；非 Windows 故障路径尚待当地运行 |
| 三次有界 retry / 安全 warning | PASS | 静态源码证据；不宣称所有 writer 已全局串行 |
| 15s / 40s 候选预算 | WARN | 完整账号 fallback 链 15s，池 40s；慢 fallback 可被截断，未证明参数最优；500ms 后启动一次确认请求，共享剩余 deadline |
| modern Hermes 默认不 patch，Retry-After contract | PASS | 已验证基线源码 + 本地 contract；legacy patch 非主路径 |
| Windows PowerShell 默认 dry-run / Apply 后配置失败 | PASS | 本机原生入口执行、真实 patch；只替换配置 writer 为明确失败 stub |
| macOS shell 默认 dry-run / 配置失败 | PASS | 本机 Git Bash 执行 shell 入口；不是 macOS 真机执行 |
| Python、JSON、shell、Rust、secret/history scan | PASS | python scripts/verify.py；pytest 50 passed / 1 skipped，unittest 12 passed；两个版本预算 harness 各8 passed |
| tracked + nonignored untracked immutability | PASS | 最终 verify 前后集合、成员身份、存在性、SHA 一致；finally 检查，无自动恢复；pytest 禁用 cacheprovider |
| 符号链接专项 | WARN | 本机不能创建测试符号链接，1 项跳过，不计通过 |
| 本轮最终版本 Windows/macOS CI | NOT_RUN | workflow_dispatch 保留，未触发；历史 CI 不充当本轮结果 |
| Windows 10/11 与 Apple Silicon Mac 全平台真机矩阵 | NOT_RUN | 当前仅本机 Windows x64 仓库层测试，不宣称矩阵完成 |
| 完整 AGT cargo/Tauri 编译及启动 | NOT_RUN | 下一阶段 |
| API key、models、chat、SSE、真实 OAuth/rotation/重启 | NOT_RUN | 下一阶段 |
| 双账号接管、真实 Retry-After/Hermes 恢复、双重启与最终服务回滚 | NOT_RUN | 下一阶段 |

## 固定边界

- 生产 AGT/Hermes 服务、账号和凭据未修改。
- Actions 仅 workflow_dispatch；完整 Windows x64/macOS arm64 配置保留，需老板当次授权才运行。
- atomic replace 不保证永久磁盘错误或进程退出前未写盘的 rotation 存活；完整真实重启验证尚未执行。
- 仓库层冻结不意味着未来发现的真实缺陷不能修，而是不再提前扩展功能。
