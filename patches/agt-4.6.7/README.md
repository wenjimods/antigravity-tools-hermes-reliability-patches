# AGT 4.6.7 Token Manager 源码根治补丁

## 背景与问题根因
在 Antigravity-Manager (AGT) v4.6.7 原始实现中，`TokenManager::get_token_filtered` 使用单一的 5 秒 `tokio::time::timeout` 约束整个账号获取流程（包含轮询、加锁、OAuth 刷新网络请求及磁盘持久化）。
当上游 Google OAuth 刷新出现网络延迟或响应稍慢（> 5 秒）时，该全局超时会直接触发：
```
Token acquisition timeout (5s) - system too busy or deadlock detected
```
从而导致客户端（如 Hermes）收到 HTTP 503 错误，并在重试过程中引发级联超时。

## 根治方案设计
本补丁对 AGT 4.6.7 的 Token 管理器进行分层超时解耦与并发安全重构：

1. **总请求安全保护提升至 40 秒 (`ACQUISITION_TIMEOUT = 40s`)**：
   - 为整轮调度提供充裕的安全兜底，留出在单个账号刷新超时后尝试池中备用账号的时间。
2. **账号级独立锁与独立网络超时 (`refresh_budget.rs`)**：
   - `LOCK_TIMEOUT = 1s`：单个账号互斥锁获取超时，避免线程锁死。
   - `REFRESH_TIMEOUT = 15s`：单次 OAuth 刷新网络请求独立超时。
3. **双重检查锁定 (Double-Checked Locking)**：
   - 在成功获取 per-account lock 后，立即重新读取内存中该账号的最新 Token 状态。若已被其他并发请求刷新完毕，直接复用最新 Token，避免重复发起 OAuth 刷新。
4. **优先内存更新与异步安全落盘**：
   - 刷新成功后，立即更新内存缓存，确保并发调度立即可用。
   - 通过 `tokio::task::spawn_blocking` 在后台异步更新本地 JSON 账号文件；并在落盘前核验文件中的 `expiry_timestamp`，防止并发后台刷新产生较旧结果覆盖较新结果的竞争。
5. **故障账号隔离与透明 Fallback**：
   - 刷新失败后，从本次请求候选中排除该账号，不返回过期旧 Token，并将网络超时与真实的 `invalid_grant` 凭据失效严格区分（超时不累计 `invalid_grant` 计数）。
   - 调度器透明切换至下一个可用账号继续处理。

## 补丁内容与结构
- `token-manager-fix.patch`：可直接通过 `patch -p1` 或 `git apply` 应用于 `lbjlaq/Antigravity-Manager` 4.6.7 源码。
- `refresh_budget.rs`：独立的超时预算与锁管理模块。
- `harness/`：独立的 Rust 回归测试 Cargo 工程，包含 8 项单元测试。

## 应用与验证
```bash
# 1. 在 AGT 源码根目录下应用补丁
git apply path/to/patches/agt-4.6.7/token-manager-fix.patch

# 2. 运行 Rust 预算与锁管理测试
cargo test --manifest-path patches/agt-4.6.7/harness/Cargo.toml
```
