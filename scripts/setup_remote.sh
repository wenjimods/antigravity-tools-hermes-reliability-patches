#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPLY=0; SRC="${AGT_SRC_DIR:-}"; CONFIG=""; VERSION="4.7.0"
while (($#)); do
  case "$1" in
    --apply) APPLY=1;;
    --config) shift; CONFIG="${1:?missing config}";;
    --version) shift; VERSION="${1:?missing version}";;
    --*) echo "Unknown option: $1" >&2; exit 2;;
    *) SRC="$1";;
  esac
  shift
done
python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"'
[[ -n "$SRC" && -d "$SRC" ]] || { echo 'Existing source directory required' >&2; exit 2; }
export PYTHONPATH="$ROOT/scripts:$ROOT/configs/agt${PYTHONPATH:+:$PYTHONPATH}"
CFG="$(python3 -c 'import sys; from platform_tools import select_config; print(select_config(sys.argv[1] or None))' "$CONFIG")"
python3 "$ROOT/configs/agt/apply_refresh_interval.py" --config "$CFG" --dry-run
python3 "$ROOT/scripts/apply_agt_patch.py" "$SRC" --version "$VERSION" --dry-run
if (( APPLY )); then
  python3 "$ROOT/scripts/apply_agt_patch.py" "$SRC" --version "$VERSION"
  python3 "$ROOT/configs/agt/apply_refresh_interval.py" --config "$CFG"
fi
