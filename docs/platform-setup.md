# 跨平台安装/预检边界

支持矩阵：Windows 10/11 x64（原生 PowerShell）、macOS Apple Silicon arm64；WinARM 为 experimental，Intel Mac 不在目标矩阵。CI 使用 `windows-2022` 与 Apple Silicon `macos-14` runner，并断言 `platform.machine()`。

所有入口默认 dry-run；仅显式 `--apply` 才调用既有补丁/配置脚本。不会下载安装工具、改变运行服务、替账号登录或自动 OAuth。要求用户已有 AGT 源码目录和完整 `gui_config.json`。

## 配置优先级

`--config` > `AGT_CONFIG_PATH` > `ABV_DATA_DIR/gui_config.json` > `AGT_CONFIG_DIR/gui_config.json` > `~/.antigravity_tools/gui_config.json`。选择到的文件必须已存在；配置修改保留未知字段、先备份并原子替换；不完整/非法配置拒绝写入。`auto_refresh=false` 只告警，不自动开启。

## Windows

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_windows.ps1 -SourceDir 'C:\含中文\AGT'
# 明确确认后才写入：加 -Apply
```

入口发现 Git PATH、`ProgramFiles/Git`、PortableGit 常见位置及 `HERMES_GIT_BASH_PATH`，并检查 `%LOCALAPPDATA%\hermes\git\usr\bin\bash.exe` / `bin\bash.exe`。路径均以 subprocess argv 传递，不拼接 shell 命令。Windows 用户不需要手动进入 Bash。

## macOS/远程

```bash
AGT_SRC_DIR='/path/已有源码' ./scripts/setup_macos.sh
AGT_SRC_DIR='/path/已有源码' ./scripts/setup_remote.sh --config /path/gui_config.json
```

## 验证

```bash
python scripts/verify.py
```

验证包含 Python 单元测试、shell 语法、JSON/秘密模式扫描；检测到 Rust harness 时先 `cargo fetch`，再 `cargo test --offline`。网络失败会明确停止并说明，不伪造通过。正式运行服务、构建和 OAuth 必须由操作者手动完成。
