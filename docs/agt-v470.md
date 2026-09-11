# AGT v4.7.0 候选补丁

固定官方 commit `85fb4fe688997d3a0c2930b7a202cf22f617b092`。baseline/ 为真实相关原始文件，after/ 为应用后文件；manifest.json记录LF归一化 before/after SHA与patch SHA。

40s acquisition guard、1s lock、15s refresh；preferred刷新失败退出专用label并排除该账号，main保留invalid_grant>=2停用规则。OAuth函数不修改。锁后读取新token，成功更新内存包括rotated refresh_token，再后台写盘；读/解析/写盘失败最多3次并warning，无凭据内容。

同源helper Rust测试覆盖预算/锁/错误/6秒真实TCP延迟；Python覆盖真实补丁apply/reverse/重复/拒绝。尚未完整AGT编译，不宣称preferred/main集成执行已被helper证明。

持久化现在复用官方 `load_account_at_path`/`save_account_at_path`：后者仅在写入阶段持有每账号锁，并使用临时文件+Windows MoveFileExW(REPLACE_EXISTING|WRITE_THROUGH)或非Windows rename。调用方保留原有全局管理锁覆盖本路径读-改-写，锁顺序与官方 upsert_account 相同：先全局锁，再进入 save 的每账号锁；save 不重新获取全局锁。每账号锁本身仍只保护写入，与不采用全局锁的其他写入路径可能交错，因此不宣称全局并发串行化。typed `Account` 保存会按官方模型序列化，模型未知/新增字段可能被丢弃，需跟随上游模型核对。故障时保留3次重试与warning；进程崩溃或永久磁盘错误仍可能丢失rotation。expiry比较不等同完整并发generation顺序证明。真正rotation→重启必须真机测试，不能宣称已保证。当前15s包住完整OAuth调用链，慢client fallback可能被截断，但超时不得计为invalid_grant。
