#!/usr/bin/env bash
# ==============================================================================
# setup_macos.sh - macOS / Unix Setup Guide & Automation for AGT Reliability Kit
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== AGT -> Hermes 8045 Reliability Kit (macOS Setup) ==="
echo "Repository Root: ${REPO_ROOT}"

# 1. Dependency Check
echo ""
echo "[Step 1/5] Checking required build dependencies..."
for tool in git python3 cargo; do
    if ! command -v "$tool" &>/dev/null; then
        echo "[-] Missing required dependency: $tool. Please install it (e.g. via Homebrew or rustup) and retry."
        exit 1
    fi
done
echo "[+] All required tools found: git, python3, cargo."

# 2. Acquire Upstream AGT v4.6.7 Source
echo ""
echo "[Step 2/5] Preparing AGT v4.6.7 source code..."
AGT_WORKSPACE="${AGT_SRC_DIR:-${REPO_ROOT}/workspace/Antigravity-Manager}"

if [ ! -d "${AGT_WORKSPACE}" ]; then
    echo "[*] Upstream source not found at ${AGT_WORKSPACE}."
    read -rp "Clone official v4.6.7 repository to workspace? [y/N]: " choice
    if [[ "$choice" =~ ^[Yy]$ ]]; then
        mkdir -p "$(dirname "${AGT_WORKSPACE}")"
        git clone --branch v4.6.7 --depth 1 https://github.com/lbjlaq/Antigravity-Manager.git "${AGT_WORKSPACE}"
    else
        read -rp "Please enter the absolute path to your local AGT 4.6.7 source tree: " AGT_WORKSPACE
    fi
fi

# 3. Apply AGT 4.6.7 Source Patch
echo ""
echo "[Step 3/5] Applying AGT 4.6.7 token manager source patch..."
python3 "${REPO_ROOT}/scripts/apply_agt_patch.py" "${AGT_WORKSPACE}"

echo "[*] Running Rust harness regression tests..."
cargo test --manifest-path "${REPO_ROOT}/patches/agt-4.6.7/harness/Cargo.toml"

# 4. Apply 2-Minute Background Refresh Mitigation
echo ""
echo "[Step 4/5] Applying 2-minute background refresh configuration..."
python3 "${REPO_ROOT}/configs/agt/apply_refresh_interval.py"

# 5. Hermes Client Configuration Template
echo ""
echo "[Step 5/5] Hermes Local 8045 Bridge Configuration..."
HERMES_CONF_DIR="${HOME}/.hermes"
mkdir -p "${HERMES_CONF_DIR}"

if [ ! -f "${HERMES_CONF_DIR}/config.yaml" ]; then
    cp "${REPO_ROOT}/configs/hermes/config.template.yaml" "${HERMES_CONF_DIR}/config.yaml"
    echo "[+] Created ${HERMES_CONF_DIR}/config.yaml from template."
else
    echo "[!] Existing ${HERMES_CONF_DIR}/config.yaml detected. Preserving existing file."
fi

echo ""
echo "=========================================================================="
echo "  [SUCCESS] macOS Setup & Patch Preparation Complete!"
echo "  - AGT Patch: Applied to ${AGT_WORKSPACE}"
echo "  - Background Interval: Set to 2m in ~/.antigravity_tools/gui_config.json"
echo "  - Hermes Config: Template available in ${HERMES_CONF_DIR}/config.yaml"
echo "  NOTE: Sensitive API Keys must only be set via environment variables (OPENAI_API_KEY)"
echo "=========================================================================="
