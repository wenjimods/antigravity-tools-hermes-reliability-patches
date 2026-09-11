# Hermes patch 说明

当前官方 Hermes commit `5d2d5e906d62e326e600855277403b8595325b38` 已在恢复路径原生处理 `Retry-After`，本仓库没有默认要求打补丁。旧 patch 仅作为历史/旧基线参考，禁止未经 source hash 对齐就应用。

本轮实证见 `docs/hermes-compatibility.md` 与 `tests/test_retry_after_contract.py`：测试从官方源码提取并执行完整 `compute_error_backoff` 函数，使用真实本地 HTTP server 产生 503/Retry-After 后再获得 200；函数返回等待值，测试显式 sleep 1 秒后重试，不把“返回 1”冒充函数内部已 sleep；没有复制重试算法，也没有发真实生成请求。

若目标 Hermes 版本不同，先取得官方 source manifest 或 commit，比较该函数及其依赖；无法取得证据时只能报告 WARN，不得声称兼容。