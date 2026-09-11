# Hermes 客户端重试补丁 (All Accounts Limited → Upstream Rate Limit)

## 背景与问题
当 Antigravity-Manager (8045 端口) 账号池中的所有账号均触发上游限流且等待时间 > 2 秒时，AGT 会返回如下格式的 503 / 错误信息：
```
All accounts limited. Wait 12s.
```
在 Hermes 默认的错误分类与重试策略中：
1. 若未能精确识别该上游限流信息，可能被判定为普通的 `server_error` 或 `overloaded`，导致默认指数退避等待时间不足，在账号池解冻前再次重试并耗尽 `max_retries`。
2. 若误判为当前 API Key 凭据耗尽，可能触发不必要的凭据轮换或提前中断会话。

## 补丁设计与实现
本补丁对 Hermes 的错误分类与重试等待流程进行最小侵入性增强：

1. **`agent/error_classifier.py`**：
   - 模式匹配新增 `_UPSTREAM_ACCOUNT_LIMITED_PATTERNS = ("all accounts limited", "all accounts rate-limited", "all accounts failed")`。
   - 在 503 与无状态消息分类中识别此类错误，归类为 `FailoverReason.upstream_rate_limit`，设置 `should_fallback=False`（保持当前渠道不盲目切走），并通过 `_extract_upstream_wait_context` 提取上游等待秒数。
2. **`agent/retry_utils.py`**：
   - 增加 `parse_upstream_wait_seconds(error_or_text)` 辅助解析函数，支持从错误消息中精确提取如 `Wait 12s`、`wait 5 seconds` 等等待秒数 `N`。
3. **`agent/turn_recovery.py` / `agent/conversation_loop.py`**：
   - 在计算重试退避等待时间 `compute_error_backoff` 时，若检测到上游全池限流错误并解析出 `N` 秒，自动采用 `N + 1.0` 秒作为本次重试的等待时间（预留 1 秒缓冲，避免网络微小抖动在上游解冻前提前到达）。

## 补丁文件
- `hermes-all-accounts-limited-retry.patch`：可直接通过 `git apply` 应用于 Hermes 仓库。

## 应用方式
```bash
# 在 hermes-agent 根目录下执行
git apply path/to/patches/hermes/hermes-all-accounts-limited-retry.patch
```
