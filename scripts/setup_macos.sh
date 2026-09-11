#!/usr/bin/env bash
# macOS preflight; no package installation, service changes, or OAuth automation.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; APPLY=0; SRC="${AGT_SRC_DIR:-${1:-}}"
for arg in "$@"; do [[ "$arg" == "--apply" ]] && APPLY=1 || [[ "$arg" == /* ]] && SRC="$arg"; done
command -v python3 >/dev/null || { echo "缺少 python3；不改文件。" >&2; exit 1; }
[[ -n "$SRC" && -d "$SRC" ]] || { echo "需要已有 AGT 源码目录；不会克隆或伪造。" >&2; exit 2; }
CFG="${AGT_CONFIG_PATH:-${HOME}/.antigravity_tools/gui_config.json}"
[[ -f "$CFG" ]] || { echo "需要已有完整配置: $CFG；不会复制模板。" >&2; exit 2; }
echo "预检通过：不安装依赖、不改运行服务、不执行 OAuth。"
if (( APPLY )); then
  python3 "$ROOT/scripts/apply_agt_patch.py" "$SRC"
  python3 "$ROOT/configs/agt/apply_refresh_interval.py" --config "$CFG"
  echo "本地候选修改完成；首次构建/启动与 OAuth 必须手工完成。"
else
  echo "仅预检。真正首次安装、构建、启动及手工 OAuth 步骤需操作者明确执行；--apply 才修改。"
fi
