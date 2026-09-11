# Hermes 8045 本地代理配置模板

## 概述
本目录提供用于连接本地/远程 Antigravity-Manager (8045 端口) 的 Hermes 客户端配置模板。

## 敏感信息管理原则
- **禁止硬编码任何明文 Key**。
- API Key 及管理凭据必须仅通过环境变量（如 `OPENAI_API_KEY`）或安全交互输入注入。

## 配置步骤
1. 复制 `env.template` 为你的私有环境变量文件（如 `~/.hermes/.env`）：
   ```bash
   cp configs/hermes/env.template ~/.hermes/.env
   ```
2. 编辑填入从 AGT 生成的 Proxy API Key。
3. 复制 `config.template.yaml` 至 `~/.hermes/config.yaml`。
