#!/usr/bin/env python3
"""Offline test suite verifying AGT 4.6.7 patch integrity and application logic."""

import pathlib
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import apply_agt_patch

class TestAgtPatchDryRun(unittest.TestCase):
    def setUp(self):
        self.patch_file = REPO_ROOT / "patches" / "agt-4.6.7" / "token-manager-fix.patch"
        self.refresh_budget_file = REPO_ROOT / "patches" / "agt-4.6.7" / "refresh_budget.rs"
        self.harness_cargo = REPO_ROOT / "patches" / "agt-4.6.7" / "harness" / "Cargo.toml"

    def test_patch_files_exist(self):
        self.assertTrue(self.patch_file.exists(), "token-manager-fix.patch must exist")
        self.assertTrue(self.refresh_budget_file.exists(), "refresh_budget.rs must exist")
        self.assertTrue(self.harness_cargo.exists(), "harness/Cargo.toml must exist")
        self.assertGreater(self.patch_file.stat().st_size, 1000)
        self.assertGreater(self.refresh_budget_file.stat().st_size, 500)

    def test_refresh_budget_syntax_and_constants(self):
        content = self.refresh_budget_file.read_text(encoding="utf-8")
        self.assertIn("pub const ACQUISITION_TIMEOUT: Duration = Duration::from_secs(40);", content)
        self.assertIn("pub const REFRESH_TIMEOUT: Duration = Duration::from_secs(15);", content)
        self.assertIn("pub const LOCK_TIMEOUT: Duration = Duration::from_secs(1);", content)
        self.assertIn("pub async fn with_refresh_lock", content)
        self.assertIn("mod tests", content)

    def test_apply_patch_on_synthetic_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmproot = pathlib.Path(tmpdir)
            proxy_dir = tmproot / "src-tauri" / "src" / "proxy"
            proxy_dir.mkdir(parents=True, exist_ok=True)

            dummy_mod = proxy_dir / "mod.rs"
            dummy_mod.write_text("// proxy module\npub mod token_manager;\n", encoding="utf-8")

            dummy_tm = proxy_dir / "token_manager.rs"
            dummy_tm.write_text(
                """// Dummy token manager
impl TokenManager {
    async fn get_token_filtered(&self) {
        // 【优化 Issue #284】添加 5 秒超时，防止死锁
        let timeout_duration = std::time::Duration::from_secs(5);
        Token acquisition timeout (5s) - system too busy or deadlock detected
        if let Some(ref pref_id) = preferred_id {
            // [NEW] 检查 token 是否过期（调整刷新时机对齐官方：90s 宽限期）
            // 确保有 project_id
        }
        // ===== [END FIX #820] =====
        // 3. [ENHANCED] 检查 token 是否过期
        tracing::error!("error");
        continue;
        // 4. [ENHANCED] 确保有 project_id
    }
}
""",
                encoding="utf-8",
            )

            # Apply patch
            success = apply_agt_patch.apply_patch(tmproot, dry_run=False)
            self.assertTrue(success, "apply_patch should succeed on valid source tree")

            # Validate applied results
            patched_tm = dummy_tm.read_text(encoding="utf-8")
            self.assertIn("ACQUISITION_TIMEOUT", patched_tm)
            self.assertIn("refresh_proxy_token", patched_tm)
            self.assertIn("Token acquisition budget exhausted (40s)", patched_tm)
            self.assertIn("break 'preferred;", patched_tm)

            patched_mod = dummy_mod.read_text(encoding="utf-8")
            self.assertIn("pub(crate) mod refresh_budget;", patched_mod)

            budget_dst = proxy_dir / "refresh_budget.rs"
            self.assertTrue(budget_dst.exists())

            # Idempotency check: running second time should report success/skip
            success_again = apply_agt_patch.apply_patch(tmproot, dry_run=False)
            self.assertTrue(success_again, "Idempotent apply_patch should succeed")

if __name__ == "__main__":
    unittest.main()
