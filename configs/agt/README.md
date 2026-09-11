# AGT 2分钟后台刷新配置缓解

## 缓解机制说明
在 Antigravity-Manager 中，`refresh_interval` 控制后台自动批处理刷新账号配额与 Token 的周期（默认通常为 15 分钟）。

将后台刷新间隔缩短为 2 分钟 (`refresh_interval = 2`) 的作用：
- **主动预热**：在账号 Token 实际过期（通常有效时长为 1 小时）前，更频繁地在后台完成刷新与换发。
- **减小前台命中率**：使得前台用户请求在到达时，极大概率命中已经在后台刷新完毕的有效 Token，从而规避前台请求直接触发同步 OAuth 网络刷新的风险。

## 局限性与非根治声明
> [!WARNING]
> 缩短后台刷新间隔属于**运维层面的配置缓解措施**，**并非根治**。
> 1. 若网络出现较大波动导致单次 OAuth 刷新请求耗时超过 5 秒，未经源码补丁修复的程序仍然会在前台触发 5 秒超时并报错 503。
> 2. 若上游 Google OAuth 接口发生故障或账号池全部受限，后台预刷新亦无法生成有效 Token。
> 3. 必须配合 `patches/agt-4.6.7/` 的源码根治补丁（将前台 5 秒死锁超时提升为 40 秒安全上限与 15 秒独立 OAuth 超时）共同使用。

## 使用方法
```bash
# 使用幂等脚本应用配置
python configs/agt/apply_refresh_interval.py
```
可通过环境变量自定义配置路径：
```bash
export AGT_CONFIG_PATH="/path/to/gui_config.json"
python configs/agt/apply_refresh_interval.py
```
