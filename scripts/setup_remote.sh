#!/usr/bin/env bash
# Safe preflight; --apply only runs local patch/test helpers, never installs or starts services.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPLY=0; SRC="${AGT_SRC_DIR:-${1:-}}"
for arg in "$@"; do [[ "$arg" == "--apply" ]] && APPLY=1 || [[ "$arg" == /* ]] && SRC="$arg"; done
for tool in python3; do command -v "$tool" >/dev/null || { echo "缺少 $tool；仅预检失败，不改文件。" >&2; exit 1; }; done
[[ -n "$SRC" && -d "$SRC" ]] || { echo "用法: $0 [--apply] /path/to/existing-AGT-source" >&2; exit 2; }
CFG="${AGT_CONFIG_PATH:-${HOME}/.antigravity_tools/gui_config.json}"
[[ -f "$CFG" ]] || { echo "需要已有完整配置: $CFG；不会创建模板。" >&2; exit 2; }
echo "预检通过：已有源代码与配置；不会安装依赖、修改运行服务或执行 OAuth。"
if (( APPLY )); then
  python3 "$ROOT/scripts/apply_agt_patch.py" "$SRC"
  python3 "$ROOT/configs/agt/apply_refresh_interval.py" --config "$CFG"
  echo "完成本地补丁/配置；请按项目文档手工构建、启动服务并完成 OAuth。"
else
  echo "仅预检。真正首次安装/构建、启动服务与 OAuth 登录须由操作者明确手工执行；使用 --apply 才修改候选源/已有配置。"
fi
