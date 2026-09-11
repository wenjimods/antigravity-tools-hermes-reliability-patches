#!/usr/bin/env python3
"""Idempotently apply the 2-minute background refresh interval mitigation to AGT config."""

import datetime
import json
import os
import pathlib
import shutil
import sys

def get_config_path() -> pathlib.Path:
    env_path = os.environ.get("AGT_CONFIG_PATH")
    if env_path:
        return pathlib.Path(env_path)
    env_dir = os.environ.get("AGT_CONFIG_DIR")
    if env_dir:
        return pathlib.Path(env_dir) / "gui_config.json"
    return pathlib.Path.home() / ".antigravity_tools" / "gui_config.json"

def apply_mitigation(config_path: pathlib.Path, target_interval: int = 2) -> bool:
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}", file=sys.stderr)
        return False

    raw_text = config_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON config: {e}", file=sys.stderr)
        return False

    old_interval = data.get("refresh_interval")
    if old_interval == target_interval:
        print(f"[OK] Config already has refresh_interval set to {target_interval}m. No change needed.")
        return True

    # Backup original configuration
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = config_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_file = backup_dir / f"gui_config_backup_{stamp}.json"
    shutil.copy2(config_path, backup_file)
    print(f"[*] Backup created at: {backup_file}")

    data["refresh_interval"] = target_interval
    config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[SUCCESS] Updated refresh_interval from {old_interval} to {target_interval} minutes.")
    return True

def main():
    target_path = get_config_path()
    print(f"Applying mitigation to: {target_path}")
    success = apply_mitigation(target_path, target_interval=2)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
