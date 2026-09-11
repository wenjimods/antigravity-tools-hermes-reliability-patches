import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import patch_core


def test_blocked_manifest_is_clear_error(tmp_path):
    (tmp_path / 'manifest.json').write_text('{"status":"BLOCKED","blocked_reason":"test"}')
    with pytest.raises(ValueError, match="BLOCKED"):
        patch_core._manifest(tmp_path)


def test_symlink_escape_is_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "src"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError, match="unsafe"):
        patch_core._safe(tmp_path, "src/file.rs")


def test_write_failure_restores_all_originals(tmp_path, monkeypatch):
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_bytes(b"old-first")
    second.write_bytes(b"old-second")
    originals = {"first.txt": b"old-first", "second.txt": b"old-second"}
    payload = {"first.txt": b"new-first", "second.txt": b"new-second"}
    real_write = Path.write_bytes
    calls = {"n": 0}

    def fail_on_second_write(path, data):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("injected write failure")
        return real_write(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_on_second_write)
    with pytest.raises(OSError, match="injected"):
        patch_core._write(tmp_path, payload, originals)
    assert first.read_bytes() == b"old-first"
    assert second.read_bytes() == b"old-second"
