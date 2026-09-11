#!/usr/bin/env python3
"""Safely set AGT AppConfig.refresh_interval (minutes) in an existing config."""
import argparse, datetime, json, os, pathlib, shutil, sys, tempfile

# Fields required by AGT v4.6.7 AppConfig; do not fabricate a partial config.
REQUIRED = {"language", "theme", "auto_refresh", "refresh_interval", "auto_sync", "sync_interval"}

def get_config_path():
    return pathlib.Path(os.environ.get("AGT_CONFIG_PATH") or pathlib.Path(os.environ.get("AGT_CONFIG_DIR", pathlib.Path.home() / ".antigravity_tools")) / "gui_config.json")

def apply_mitigation(config_path, target_interval=2):
    config_path = pathlib.Path(config_path)
    if not config_path.is_file():
        print(f"Error: existing config required: {config_path}", file=sys.stderr); return False
    try:
        raw = config_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"Error: invalid config (unchanged): {exc}", file=sys.stderr); return False
    if not isinstance(data, dict) or not REQUIRED.issubset(data):
        missing = sorted(REQUIRED - set(data) if isinstance(data, dict) else REQUIRED)
        print(f"Error: incomplete AGT AppConfig; missing {missing} (unchanged)", file=sys.stderr); return False
    if isinstance(data["refresh_interval"], bool) or not isinstance(data["refresh_interval"], int) or data["refresh_interval"] < 1:
        print("Error: refresh_interval must be a positive integer in minutes (unchanged)", file=sys.stderr); return False
    if isinstance(target_interval, bool) or not isinstance(target_interval, int) or target_interval < 1:
        print("Error: target interval must be a positive integer (unchanged)", file=sys.stderr); return False
    if data["refresh_interval"] == target_interval:
        print(f"[OK] refresh_interval={target_interval} minutes; unchanged"); return True
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = config_path.with_name(f"{config_path.name}.backup-{stamp}")
    try:
        shutil.copy2(config_path, backup)
        data["refresh_interval"] = target_interval
        payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        fd, tmp = tempfile.mkstemp(prefix=f".{config_path.name}.", dir=config_path.parent, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle: handle.write(payload); handle.flush(); os.fsync(handle.fileno())
            os.replace(tmp, config_path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    except (OSError, UnicodeError) as exc:
        print(f"Error: update failed; original preserved: {exc}", file=sys.stderr); return False
    print(f"[OK] backup={backup}; refresh_interval={target_interval} minutes"); return True

def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config", type=pathlib.Path, default=get_config_path()); parser.add_argument("--interval", type=int, default=2)
    args = parser.parse_args(); raise SystemExit(0 if apply_mitigation(args.config, args.interval) else 1)
if __name__ == "__main__": main()
