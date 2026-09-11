# Hermes 兼容性实证

## 当前结论

本仓库以官方 Hermes commit `5d2d5e906d62e326e600855277403b8595325b38` 的精确源码副本为证据。`compute_error_backoff` 通过官方 `agent.retry_utils` 解析 `Retry-After`；有效值优先于 legacy jitter backoff，并封顶 600 秒，适用于可重试 5xx。测试启动真实本地 HTTP server：首个响应为 `503 + Retry-After: 1`，实际调用官方函数得到 1 秒，再次请求得到 200。该测试不是 SDK 独立重试，也不是生产 E2E。

未提供本地 Hermes source manifest/hash 或运行时版本信息时，doctor 对版本只报告 `WARN: not verified`，不使用 hardcode `SUPPORTED` 冒充检查。

## doctor 安全契约

`python scripts/check_stack.py` 是只读检查，不发送生成请求：

- 默认仅允许 loopback；远端必须显式 `--allow-remote` 且必须 HTTPS。
- 拒绝 URL 用户名/密码、query、fragment；`/v1` 与 `/v1/models` 不会重复拼接。
- 禁止自动跟随重定向，避免 Bearer 泄漏；key 仅来自环境变量或 stdin，输出不包含 key。
- 检查无 key、错 key、正确 key；offline、鉴权异常、超时非法范围为 FAIL；缺版本证据为 WARN。
- timeout 必须为 0.1–60 秒。

## 支持边界

| 维度 | 状态 | 证据 |
|---|---|---|
| Hermes 官方 commit | 源码/contract 已验证 | `tests/test_retry_after_contract.py` |
| 503 Retry-After → 200 | 本地 HTTP executable contract 已验证 | 真实 server + 官方函数 |
| AGT v4.7 完整 E2E | NOT_RUN / blocked | 无真实部署与授权环境 |
| Windows 10/11 x64 | 工具契约可测 | 不等同生产 Hermes E2E；真机 `NOT_RUN` |
| macOS Apple Silicon | 目标平台 | 真机 `NOT_RUN` |
| Windows ARM | 实验性目标 | 真机 `NOT_RUN`，不作承诺 |
| Intel Mac | 不承诺 | 不纳入支持矩阵 |

旧 `patches/hermes/hermes-all-accounts-limited-retry.patch` 仅供旧基线审查；Hermes legacy 不强制 patch，当前版本不要机械套用。