# AGT → Hermes 8045 Reliability Kit

可复现地维护三层可靠性改进，适用于本地或远程电脑：

1. **AGT v4.6.7 源码修复**：将账号获取总安全预算设为 40 秒；账号锁 1 秒、OAuth 刷新 15 秒；锁后重读；刷新失败排除当前账号并继续换号。
2. **Hermes 客户端修复**：识别 `All accounts limited. Wait Ns.`，按 `N + 1` 秒重试，不把上游账号池限流误判为本地凭据失效。
3. **配置缓解**：AGT 后台刷新间隔 2 分钟，降低前台同步刷新概率；这不是根治方案，也不能消除所有 503。

## 使用

```bash
python scripts/apply_agt_patch.py /path/to/Antigravity-Manager
python scripts/apply_hermes_patch.py /path/to/hermes-agent
python configs/agt/apply_refresh_interval.py /path/to/gui_config.json
```

远程电脑可先将仓库复制到目标机，再执行同样命令；`scripts/setup_macos.sh` 和 `scripts/setup_remote.sh` 只安装/检查本地工具，不接触账号数据。API Key 仅通过目标环境的私有环境变量注入，模板不含凭据。

## 验证

```bash
python -m unittest discover -s tests -v
```

## 边界

本仓库不包含真实账号、Token、Cookie、API Key、数据库、日志、二进制、内部域名或机器绝对路径。上游项目为 `lbjlaq/Antigravity-Manager`，基线 v4.6.7；许可证与归属见 `LICENSE` 和 `NOTICE.md`。
