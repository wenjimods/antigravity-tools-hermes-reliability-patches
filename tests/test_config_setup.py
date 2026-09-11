import json, pathlib, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "configs" / "agt"))
import apply_refresh_interval as refresh

COMPLETE = {"language":"zh", "theme":"system", "auto_refresh":True, "refresh_interval":15, "auto_sync":False, "sync_interval":5}

class TestConfigSetup(unittest.TestCase):
    def test_real_complete_config_is_updated_backed_up_and_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "gui_config.json"; p.write_text(json.dumps(COMPLETE), encoding="utf-8")
            self.assertTrue(refresh.apply_mitigation(p)); self.assertEqual(json.loads(p.read_text())["refresh_interval"], 2)
            backups = list(pathlib.Path(d).glob("gui_config.json.backup-*")); self.assertEqual(len(backups), 1)
            self.assertTrue(refresh.apply_mitigation(p)); self.assertEqual(len(list(pathlib.Path(d).glob("gui_config.json.backup-*"))), 1)
    def test_incomplete_invalid_and_bad_interval_leave_bytes_unchanged(self):
        for value in [{"language":"zh"}, {**COMPLETE, "refresh_interval":0}, {**COMPLETE, "refresh_interval":"2"}]:
            with tempfile.TemporaryDirectory() as d:
                p = pathlib.Path(d) / "gui_config.json"; original = json.dumps(value); p.write_text(original, encoding="utf-8")
                self.assertFalse(refresh.apply_mitigation(p)); self.assertEqual(p.read_text(encoding="utf-8"), original); self.assertEqual(list(pathlib.Path(d).iterdir()), [p])
    def test_v467_source_evidence_is_minutes(self):
        source = (ROOT / "patches/agt-4.6.7/baseline/src-tauri/src/models/config.rs").read_text(encoding="utf-8")
        self.assertIn("pub refresh_interval: i32, // minutes", source); self.assertIn("refresh_interval: 15", source)
    def test_shell_syntax(self):
        for name in ("setup_macos.sh", "setup_remote.sh"):
            r = subprocess.run(["bash", "-n", str(ROOT / "scripts" / name)], capture_output=True, text=True); self.assertEqual(r.returncode, 0, r.stderr)

if __name__ == "__main__": unittest.main()
