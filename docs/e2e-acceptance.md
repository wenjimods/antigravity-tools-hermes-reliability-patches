# E2E 验收清单

状态约定：`NOT_RUN` 不是通过。本轮不改生产服务、不发真实生成请求。

## 已完成的离线/本地证据

- [x] doctor 本地 HTTP auth matrix：无 key / 错 key / 正确 key。
- [x] doctor 禁止 redirect，验证 Bearer 不跨 redirect 转发。
- [x] doctor URL 策略、`/v1` 匹配、offline FAIL、timeout 范围、secret-safe 输出。
- [x] 官方 Hermes `compute_error_backoff`：真实本地 server 的 503 `Retry-After: 1` → 等待值 1 → 第二次响应 200。

## 未完成的真实 E2E

- [ ] 记录目标机 Hermes 与 AGT 的真实版本、source manifest/hash 和配置路径；缺证据不得宣称版本兼容。
- [ ] 独立账号完成 refresh rotation、刷新失败换号、cooldown、重启与 rollback。
- [ ] 真实 AGT endpoint 验证无/错/正确 key，以及 chat 非流式和 SSE；禁止用 stub 代替。
- [ ] 真实部署验证 503 `Retry-After` 与无 header 的 legacy backoff。
- [ ] Windows 10/11 x64 和 macOS Apple Silicon 分开记录，不能用 CI 代替真机；Windows ARM 仅实验性，Intel Mac 不承诺。

## 阻塞

当前没有生产权限、独立 OAuth 环境、目标 macOS 真机或完整 AGT v4.7 部署证据，因此完整 E2E 状态为 `NOT_RUN`。