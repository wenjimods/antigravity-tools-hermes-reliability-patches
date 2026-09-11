#!/usr/bin/env bash
# ==============================================================================
# setup_remote.sh - Remote / Headless Linux Setup Guide & Automation
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== AGT -> Hermes 8045 Reliability Kit (Remote/Linux Setup) ==="
echo "Repository Root: ${REPO_ROOT}"

# 1. Environment and Tool Validation
echo ""
echo "[Step 1/4] Verifying required build tools..."
for tool in git python3 cargo; do
    if ! command -v "$tool" &>/dev/null; then
        echo "[-] Missing dependency: $tool. Please install before proceeding."
        exit 1
    fi
done
echo "[+] Build toolchain verified."

# 2. Upstream AGT Source Path
AGT_SRC="${AGT_SRC_DIR:-${1:-}}"
if [ -z "${AGT_SRC}" ]; then
    echo "Usage: $0 /path/to/Antigravity-Manager-source"
    echo "Or export AGT_SRC_DIR=/path/to/Antigravity-Manager-source"
    exit 1
fi

if [ ! -d "${AGT_SRC}" ]; then
    echo "[ERROR] Directory does not exist: ${AGT_SRC}"
    exit 1
fi

# 3. Apply AGT Source Patch & Run Harness
echo ""
echo "[Step 2/4] Applying AGT 4.6.7 reliability patch to: ${AGT_SRC}"
python3 "${REPO_ROOT}/scripts/apply_agt_patch.py" "${AGT_SRC}"

echo "[Step 3/4] Running Rust unit test harness..."
cargo test --manifest-path "${REPO_ROOT}/patches/agt-4.6.7/harness/Cargo.toml"

# 4. Apply Configuration Mitigation
echo ""
echo "[Step 4/4] Applying background refresh interval mitigation..."
python3 "${REPO_ROOT}/configs/agt/apply_refresh_interval.py"

echo ""
echo "=========================================================================="
echo "  [SUCCESS] Remote Setup Finished Cleanly!"
echo "  Next Steps:"
echo "  1. Build candidate: cd ${AGT_SRC} && cargo build --release"
echo "  2. Point Hermes to http://127.0.0.1:8045/v1 using templates in configs/hermes/"
echo "=========================================================================="
