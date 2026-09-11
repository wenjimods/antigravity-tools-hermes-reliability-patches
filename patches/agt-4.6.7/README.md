# AGT v4.6.7 固定基线补丁

准确基线、每个目标文件的修改前后 SHA256、补丁校验值见 `manifest.json`（按 LF 归一化）。`baseline/` 保留真实上游源码测试夹具，不依赖本机绝对路径。

AGT 基线来自官方 `v4.6.7` 原始文件，本轮在线取回并核对历史原版哈希；Hermes 基线来自源码 Git commit `4a39a3ff8bea45ab5a6b646ce26ced88a8fed079`。不宣称兼容其他版本。

从工具包根目录运行 `python scripts/apply_agt_patch.py /path/to/source --dry-run`；去掉 `--dry-run` 才写入。应用器在临时目录真实应用补丁并核验全部输出哈希，未知版本/部分修改不写，完整已应用状态重复执行直接成功。只约束目标文件；不要求其他无关文件 clean。写入异常尝试恢复原文件，但断电中断不具备跨文件事务保证，因此只用于隔离副本。

`python scripts/verify.py --rust` 包含真实基线 apply、reverse-check、幂等、修改拒绝和 helper 同一性测试。Hermes 测试执行应用后源码中的 parser 与等待分支 AST，不再维护复制逻辑。AGT Rust harness 测试的是同一个生产 helper，不是完整应用编译。

Hermes 仅识别 `All accounts limited. Wait Ns` 格式；只有缺少已有 Retry-After 时才采用 `min(N+1,600)`，分类保留 `should_fallback=True`，由现有恢复逻辑决定切换。不要解读为所有错误都强制等 N+1。

本轮未进行完整 AGT 编译或 Mac 部署。上游归属和许可证见根目录 NOTICE.md。
