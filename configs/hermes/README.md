# Hermes 本地 AGT 接入

运行 `hermes model`，选择自定义 OpenAI-compatible provider，地址填写 `http://127.0.0.1:8045/v1`，模型名称从目标 AGT 的模型列表选择，按提示在目标机私下输入 Key。用 `hermes config path` 确认当前 profile。

`config.template.yaml` 仅说明可合并的 model 字段，不是完整配置。不要覆盖现有 config.yaml 或 .env，不假设 `${VAR}` 会自动展开。`env.template` 仅为提醒，不提供自动注入方案。

首次真实请求和流式调用必须在目标机另行验收，本工具包离线测试不代表接入成功。
