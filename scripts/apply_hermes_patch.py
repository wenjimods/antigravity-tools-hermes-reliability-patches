#!/usr/bin/env python3
"""Cross-platform script to idempotently apply the Hermes client retry patch."""

import argparse
import os
import pathlib
import subprocess
import sys

def apply_patch(hermes_dir: pathlib.Path, dry_run: bool = False) -> bool:
    hermes_dir = hermes_dir.resolve()
    if not hermes_dir.exists():
        print(f"[ERROR] Directory does not exist: {hermes_dir}", file=sys.stderr)
        return False

    ec_file = hermes_dir / "agent" / "error_classifier.py"
    ru_file = hermes_dir / "agent" / "retry_utils.py"

    if not ec_file.exists() or not ru_file.exists():
        print(f"[ERROR] Invalid Hermes directory structure. Missing {ec_file} or {ru_file}", file=sys.stderr)
        return False

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    patch_file = repo_root / "patches" / "hermes" / "hermes-all-accounts-limited-retry.patch"

    if not patch_file.exists():
        print(f"[ERROR] Patch file not found at {patch_file}", file=sys.stderr)
        return False

    # Check if already applied
    ec_content = ec_file.read_text(encoding="utf-8")
    if "all accounts limited" in ec_content and "parse_upstream_wait_seconds" in ru_file.read_text(encoding="utf-8"):
        print("[INFO] Hermes retry patch is already applied. Skipping.")
        return True

    print(f"[*] Applying Hermes patch to: {hermes_dir}")
    if dry_run:
        print("[DRY-RUN] Checking git apply compatibility...")
        res = subprocess.run(["git", "apply", "--check", str(patch_file)], cwd=str(hermes_dir), capture_output=True, text=True)
        if res.returncode == 0:
            print("[DRY-RUN] Patch applies cleanly!")
            return True
        else:
            print(f"[DRY-RUN] git apply --check reported:\n{res.stderr}")
            return False

    res = subprocess.run(["git", "apply", "--whitespace=fix", str(patch_file)], cwd=str(hermes_dir), capture_output=True, text=True)
    if res.returncode == 0:
        print("[SUCCESS] Hermes patch applied successfully via git apply.")
        return True
    else:
        print(f"[ERROR] git apply failed:\n{res.stderr}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Apply Hermes client retry patch")
    parser.add_argument("hermes_dir", nargs="?", help="Path to hermes-agent repository")
    parser.add_argument("--dry-run", action="store_true", help="Test application without modifying files")
    args = parser.parse_args()

    target_dir = args.hermes_dir
    if not target_dir:
        target_dir = os.environ.get("HERMES_AGENT_DIR")
    if not target_dir:
        print("Please provide path to hermes-agent directory:")
        target_dir = input("Path: ").strip()

    success = apply_patch(pathlib.Path(target_dir), dry_run=args.dry_run)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
