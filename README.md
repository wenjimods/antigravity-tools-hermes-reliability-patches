# AGT → Hermes 8045 Reliability Kit

这是**源码补丁与配置辅助包**，不是 AGT 安装器，也不是已部署的 Mac 服务。三层组件可独立使用：

| 组件 | 处理的问题 | 不处理的问题 |
|---|---|---|
| AGT v4.6.7 源码补丁 | 令牌获取总预算 40 秒、锁 1 秒、OAuth 15 秒；锁后重读；刷新失败后尝试其他账号 | 账号额度耗尽、地区限制、全部账号刷新失败 |
| Hermes 客户端补丁 | 识别 `All accounts limited. Wait Ns`，按 `N + 1` 等待后进行有界重试 | AGT 的 OAuth 刷新超时本身 |
| AGT 配置缓解 | 缩短后台刷新周期，降低请求路径碰到刷新窗口的概率 | 不能替代源码修复，不能保证消除所有 503 |

## 最短使用路径

1. 在**隔离副本**中准备上游源码，按 `patches/agt-4.6.7/README.md`、`patches/hermes/README.md` 对齐各自基线。应用器拒绝未知/部分修改的目标；不要强制覆盖。
2. 使用 Python 3.11+ 和 Git：

```bash
python scripts/apply_agt_patch.py /path/to/Antigravity-Manager
python scripts/apply_hermes_patch.py /path/to/hermes-agent
```

3. 补丁应用成功不等于程序已安装。AGT 须按官方构建说明在目标平台编译；Hermes 须在独立安装中验证，再考虑切换。不要向现用程序目录直接复制旧版本源码。
4. 首次安装 AGT 时先用官方程序生成完整配置，并由用户手工完成 OAuth。关闭目标 AGT 后，参见 `configs/agt/README.md` 对**已有完整配置**执行备份和刷新周期调整。模板只是字段说明，不是完整配置文件。
5. Hermes 接入方式见 `configs/hermes/README.md`。密钥只放目标机私有配置；不要提交账号或密钥。

`scripts/setup_macos.sh` / `scripts/setup_remote.sh` 是本地预检与引导，不自动安装应用、授权账号、创建隧道或切换流量。独立备用 Mac 使用独立账号；不复制主机账号目录，不改现有 Windows 节点。

## 离线验收

```bash
python scripts/verify.py
# 已有 Rust 工具链及本地依赖缓存时，追加真实 Rust helper 测试：
python scripts/verify.py --rust
```

入口包含源码补丁回归测试、Python/JSON 检查、Shell 语法检查和工作树/可达历史的常见密钥及个人路径模式扫描。具体真实基线与测试覆盖见各组件说明。扫描只是模式检查，不是不存在敏感内容的保证；正式推送还须审查所有文件及 Git 作者信息。

## 交付与升级边界

- 本轮只验收离线工具包；**未在 Mac 上构建、未部署、未验证目标机真实 API**。这些不能用模拟测试替代。
- 升级 AGT/Hermes 后先比较上游语义；若已修复就不要机械重打旧补丁。文件哈希不匹配时停止，不使用模糊替换兜底。
- 正式运行验收应另测：无/错/正确 Key、非流式与流式、刷新失败换号、重启恢复。测试期间保持原服务和回滚副本不动。
- 仓库不含账号、Token、Cookie、真实 Key、数据库、日志、二进制、内部域名及机器绝对路径。
- GitHub 创建、推送与公开不属于这次本地修复；发布前需确认账号、可见性、Git 历史隐私及许可证。

上游 AGT 为 `lbjlaq/Antigravity-Manager`；Hermes 为 `NousResearch/hermes-agent`。AGT 的 **CC-BY-NC-SA 4.0 非商业限制**不可忽略；许可证与第三方归属见 `LICENSE` 和 `NOTICE.md`。
