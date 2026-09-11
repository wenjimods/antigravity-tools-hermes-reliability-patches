# AGT 刷新周期缓解

AGT v4.6.7 的 `src-tauri/src/models/config.rs` 声明 `refresh_interval: i32`，单位 minutes，默认 15。源码证据保存在补丁 baseline 夹具。

先由官方程序生成完整配置并退出目标应用，再运行：

```bash
python configs/agt/apply_refresh_interval.py --config /path/to/gui_config.json --interval 2
```

脚本检查关键必需字段、保存同目录唯一备份后原子替换；不是完整 schema 验证器。非法/缺少配置不写入。不会修改 auto_refresh：需确认目标应用已开启自动刷新；无头模式的定时刷新是否生效必须在目标机实测，不能只凭字段断言。

此项仅降低请求时同步刷新的概率，不保证令牌预刷新，也不保证消除所有503。备份可能含私密配置，请留在目标机并妥善保护。
