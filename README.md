# Antigravity Tools 与 Hermes 可靠性修复

令牌刷新超时、失败换号与限流重试。**这是源码补丁与验证工具，不是万能安装器，也不是已经部署的服务。**

## 用哪个版本

| 组件 | 版本与状态 |
|---|---|
| AGT 4.7.0 | 独立候选补丁；官方 commit `85fb4fe688997d3a0c2930b7a202cf22f617b092`；真实基线 apply / dry-run / repeat / rollback 与同源 Rust helper 测试 |
| AGT 4.6.7 | 原有补丁保留，必须显式选择对应版本 |
| 当前官方 Hermes | 以 commit `5d2d5e906d62e326e600855277403b8595325b38` 验证原生 Retry-After；默认不打 Hermes 补丁 |
| 旧 Hermes 补丁 | legacy compatibility，仅适用于其精确基线及缺少标准 header 的旧环境 |

AGT 改动：40 秒总预算、1 秒账号锁、15 秒刷新预算、锁后重读、preferred/main 失败换号；保留 v4.7 的 invalid_grant 两次确认。持久化失败记录不含凭据的 warning，并有界重试。**不保证消除所有503；未完成完整 AGT 编译或 rotation 重启真机验证。**

## 目标平台

| 平台 | 定位 |
|---|---|
| Windows 10/11 x64 | 正式目标；本机 Windows 原生 PowerShell 路径已测试 |
| macOS Apple Silicon | 正式目标；CI 使用 macos-14 arm64，不等于用户 Mac 真机部署 |
| Windows ARM64 | experimental，未验原生 AGT 构建 |
| Intel Mac | 不承诺支持 |

GitHub Actions 使用 Windows Server 2022 x64 与 macOS 14 arm64；实际结果见本分支 Actions，workflow 存在不等于通过。两平台完整服务 E2E 均未完成。

## 怎么补

仅在隔离源码和非生产配置副本上操作。先由官方 AGT 初始化完整 gui_config.json；关闭候选应用，不自动OAuth、不复制生产账号、不切流量。

Windows PowerShell（默认真实 dry-run，`-Apply` 才写）：

```powershell
.\scripts\setup_windows.ps1 -SourceDir 'D:\candidate source' -Config 'D:\candidate data\gui_config.json' -Version 4.7.0
```

macOS（默认 dry-run，`--apply` 才写）：

```bash
bash scripts/setup_macos.sh /path/to/source --config /path/to/gui_config.json --version 4.7.0
```

只应用源码补丁：

```bash
python scripts/apply_agt_patch.py /path/to/source --version 4.7.0 --dry-run
# 去掉 --dry-run 才实际写入
```

配置路径优先级：`--config` > `AGT_CONFIG_PATH` > `ABV_DATA_DIR/gui_config.json` > `AGT_CONFIG_DIR/gui_config.json` > 默认目录。高优先路径不存在就拒绝，不回落到其他配置。

## 怎么验、怎么退

```bash
python -m pip install pytest
python scripts/verify.py
python scripts/check_stack.py
python scripts/apply_agt_patch.py /path/to/source --version 4.7.0 --rollback --dry-run
```

去掉 rollback 命令的 `--dry-run` 才还原。rollback 只接受 exact-after；未知或半修改状态拒绝。配置备份留在原配置旁，含敏感内容，不提交仓库。多文件写入遇普通异常会恢复，但不承诺断电事务安全。

统一验收包括 Python 全套、原生 Windows 入口、shell语法、两个同源 Rust harness、文件/历史模式扫描。首次 cargo fetch 需要网络；依赖缓存后离线运行。不打印Key；doctor不发生成请求、不跟随重定向。

## 尚需真机验收

完整 AGT 编译、真实OAuth刷新及rotation持久化、两账号失败切换、AGT→未修改Hermes恢复、chat/SSE、重启恢复与Windows/macOS真机验收仍待完成，详见 [E2E清单](docs/e2e-acceptance.md)。helper测试和本地HTTP契约不能替代这些项目。

许可证：AGT 为 CC-BY-NC-SA 4.0，Hermes 为 MIT，见 NOTICE.md；非商业限制保留。本仓库保持私有，候选分支供复核，不应直接升级生产服务。
