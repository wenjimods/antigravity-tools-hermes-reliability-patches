# AGT v4.7.0 候选补丁

固定官方 commit `85fb4fe688997d3a0c2930b7a202cf22f617b092`。baseline 仅包含官方真实存在的相关文件；`src-tauri/src/proxy/refresh_budget.rs` 在官方不存在，manifest 的 before 为 null，patch 使用 `/dev/null` 新增语义。rollback 必须删除该新增文件。仓库补丁根目录的 `refresh_budget.rs` 是同源测试 helper，不属于官方 baseline，保留供 harness 使用。

保持 40s acquisition、1s lock、15s 单账号完整 OAuth fallback 链 deadline；15s 并非单次 HTTP timeout，也不是已证明最优参数。上游请求配置及二次确认共享 deadline 的分层证据见 docs/oauth-budget.md；最终参数待真实 E2E/慢网络数据决定。

持久化使用 serde_json::Value，仅修改五个 token 字段，不再进行 typed `Account` 往返，保留未知顶层及 token 字段。窄接口 `atomic_write_account_json` 复用官方每账号锁、UUID 临时文件、Windows MoveFileExW(REPLACE_EXISTING|WRITE_THROUGH) / 非 Windows rename；失败清理临时文件。保留 caller 全局锁，顺序为全局锁→每账号锁，与上游管理路径一致；不宣称全局并发串行化或所有 account writer 已统一。后台最多三次有界重试，warning 不输出凭据。

本地回归执行真实提取的 JSON 修改块及 atomic helper：模拟账号数据的未知字段保留、rotation 字段更新；Windows 原生文件共享锁阻止替换时，旧文件字节保留且临时文件清理。非 Windows 故障路径仍需当地验证。补丁测试覆盖 dry-run/apply/重复操作/rollback 删除新增文件及 unknown/partial 拒绝，不降低 exact hash 检查。

边界：atomic replace 不等于 refresh rotation 已完成真机重启验证；永久磁盘失败或写盘前进程退出仍可能丢失 rotation。expiry 比较不证明并发 generation 全序。完整 AGT 编译、真实 OAuth、rotation→AGT 重启、双账号切换、官方未修改 Hermes chat/SSE/503 Retry-After、跨平台真机 E2E 尚未完成。生产服务未修改，Actions 仅手动触发。
