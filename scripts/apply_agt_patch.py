#!/usr/bin/env python3
"""Cross-platform script to idempotently apply the AGT 4.6.7 token manager reliability patch."""

import argparse
import os
import pathlib
import subprocess
import sys

def apply_patch(agt_src_dir: pathlib.Path, dry_run: bool = False) -> bool:
    agt_src_dir = agt_src_dir.resolve()
    if not agt_src_dir.exists():
        print(f"[ERROR] Source directory does not exist: {agt_src_dir}", file=sys.stderr)
        return False

    token_mgr = agt_src_dir / "src-tauri" / "src" / "proxy" / "token_manager.rs"
    proxy_mod = agt_src_dir / "src-tauri" / "src" / "proxy" / "mod.rs"
    refresh_budget_dst = agt_src_dir / "src-tauri" / "src" / "proxy" / "refresh_budget.rs"

    if not token_mgr.exists() or not proxy_mod.exists():
        print(f"[ERROR] Invalid AGT source tree. Missing {token_mgr} or {proxy_mod}", file=sys.stderr)
        return False

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    patch_file = repo_root / "patches" / "agt-4.6.7" / "token-manager-fix.patch"
    refresh_budget_src = repo_root / "patches" / "agt-4.6.7" / "refresh_budget.rs"

    if not patch_file.exists() or not refresh_budget_src.exists():
        print(f"[ERROR] Missing patch assets in {repo_root}", file=sys.stderr)
        return False

    # Check if already applied
    tm_content = token_mgr.read_text(encoding="utf-8")
    if "ACQUISITION_TIMEOUT" in tm_content and "refresh_proxy_token" in tm_content:
        print("[INFO] AGT token manager patch is already applied. Skipping.")
        return True

    print(f"[*] Applying AGT patch to: {agt_src_dir}")
    if dry_run:
        print("[DRY-RUN] Checking git apply compatibility...")
        res = subprocess.run(["git", "apply", "--check", str(patch_file)], cwd=str(agt_src_dir), capture_output=True, text=True)
        if res.returncode == 0:
            print("[DRY-RUN] Patch applies cleanly!")
            return True
        else:
            print(f"[DRY-RUN] git apply --check reported:\n{res.stderr}")
            return False

    # Try git apply first
    res = subprocess.run(["git", "apply", "--whitespace=fix", str(patch_file)], cwd=str(agt_src_dir), capture_output=True, text=True)
    if res.returncode == 0:
        print("[SUCCESS] git apply succeeded cleanly.")
        return True

    print(f"[WARN] git apply returned {res.returncode}: {res.stderr.strip()}. Attempting programmatic fallback application...")
    
    # Programmatic application fallback
    try:
        # 1. Copy refresh_budget.rs
        refresh_budget_dst.write_text(refresh_budget_src.read_text(encoding="utf-8"), encoding="utf-8")
        print("  - Wrote src-tauri/src/proxy/refresh_budget.rs")

        # 2. Update mod.rs
        mod_text = proxy_mod.read_text(encoding="utf-8")
        if "pub(crate) mod refresh_budget;" not in mod_text:
            proxy_mod.write_text(mod_text + "\npub(crate) mod refresh_budget;\n", encoding="utf-8")
            print("  - Registered refresh_budget in src-tauri/src/proxy/mod.rs")

        # 3. Update token_manager.rs
        method_snippet = '''    /// Refresh a single account with an independent deadline. No global lock
    /// is held over network I/O; recheck token state after acquiring its mutex.
    async fn refresh_proxy_token(&self, token: &mut ProxyToken, buffer: i64) -> Result<(), String> {
        if chrono::Utc::now().timestamp() < token.timestamp - buffer { return Ok(()); }
        let refresh_mu = self.refresh_locks.entry(token.account_id.clone())
            .or_insert_with(|| Arc::new(tokio::sync::Mutex::new(()))).clone();
        super::refresh_budget::with_refresh_lock(&refresh_mu, async {
            let latest = self.tokens.get(&token.account_id).map(|r| r.clone())
                .ok_or_else(|| "Account removed during token refresh".to_string())?;
            *token = latest;
            if chrono::Utc::now().timestamp() < token.timestamp - buffer { return Ok(()); }
            let response = crate::modules::oauth::refresh_access_token(
                &token.refresh_token, Some(&token.account_id)).await?;
            if response.expires_in <= 0 { return Err("Refreshed token has no valid lifetime".into()); }
            let expiry = chrono::Utc::now().timestamp() + response.expires_in;
            token.access_token = response.access_token.clone();
            token.expires_in = response.expires_in;
            token.timestamp = expiry;
            if let Some(ref rt) = response.refresh_token { token.refresh_token = rt.clone(); }
            if let Some(mut entry) = self.tokens.get_mut(&token.account_id) {
                entry.access_token = token.access_token.clone();
                entry.expires_in = token.expires_in;
                entry.timestamp = expiry;
                entry.refresh_token = token.refresh_token.clone();
            } else { return Err("Account removed during token refresh".into()); }
            self.invalid_grant_failures.remove(&token.account_id);
            let write_path = token.account_path.clone();
            tokio::task::spawn_blocking(move || {
                let Ok(_lk) = crate::modules::account::lock_account_file_updates() else { return; };
                let Ok(raw) = std::fs::read_to_string(&write_path) else { return; };
                let Ok(mut val) = serde_json::from_str::<serde_json::Value>(&raw) else { return; };
                if val["token"]["expiry_timestamp"].as_i64().unwrap_or(0) > expiry { return; }
                val["token"]["access_token"] = response.access_token.into();
                val["token"]["expires_in"] = response.expires_in.into();
                val["token"]["expiry_timestamp"] = expiry.into();
                if let Some(it) = response.id_token { val["token"]["id_token"] = it.into(); }
                if let Some(rt) = response.refresh_token { val["token"]["refresh_token"] = rt.into(); }
                if let Ok(data) = serde_json::to_string_pretty(&val) { let _ = std::fs::write(&write_path, data); }
            });
            Ok(())
        }).await
    }

'''
        s = tm_content
        if "async fn refresh_proxy_token" not in s:
            s = s.replace("    async fn get_token_filtered(", method_snippet + "    async fn get_token_filtered(", 1)
        s = s.replace(
            "// 【优化 Issue #284】添加 5 秒超时，防止死锁\n        let timeout_duration = std::time::Duration::from_secs(5);",
            "// Final request safety net; individual OAuth/lock deadlines allow account fallback.\n        let timeout_duration = super::refresh_budget::ACQUISITION_TIMEOUT;",
            1
        )
        s = s.replace("Token acquisition timeout (5s) - system too busy or deadlock detected", "Token acquisition budget exhausted (40s)", 1)
        s = s.replace("        if let Some(ref pref_id) = preferred_id {", "        'preferred: {\n        if let Some(ref pref_id) = preferred_id {", 1)
        s = s.replace("        // ===== [END FIX #820] =====", "        } // preferred fast path\n        // ===== [END FIX #820] =====", 1)
        
        pref_anchor = "                            // [NEW] 检查 token 是否过期（调整刷新时机对齐官方：90s 宽限期）"
        if pref_anchor in s:
            a = s.index(pref_anchor)
            b = s.index("                            // 确保有 project_id", a)
            s = s[:a] + '''                            if let Err(error) = self.refresh_proxy_token(&mut token, 90).await {
                                tracing::warn!("Preferred account refresh failed; trying remaining accounts: {}", error);
                                tokens_snapshot.retain(|t| t.account_id != token.account_id);
                                total = tokens_snapshot.len();
                                if total == 0 { return Err(error); }
                                break 'preferred;
                            }

''' + s[b:]
        elif "'preferred: {" in s and "break 'preferred;" not in s:
            s = s.replace("        } // preferred fast path", "        break 'preferred;\n        } // preferred fast path", 1)

        main_anchor = "            // 3. [ENHANCED] 检查 token 是否过期"
        if main_anchor in s:
            a = s.index(main_anchor)
            b = s.index("            // 4. [ENHANCED] 确保有 project_id", a)
            original = s[a:b]
            e = original.index("                                tracing::error!(")
            f = original.index("                                continue;", e) + len("                                continue;")
            errorblock = original[e:f]
            s = s[:a] + '''            // Per-account timeout errors use the same fallback path as OAuth failures.
            if let Err(e) = self.refresh_proxy_token(&mut token, 300).await {
''' + errorblock + '''\n            }

''' + s[b:]

        token_mgr.write_text(s, encoding="utf-8")
        print("  - Applied modifications to token_manager.rs")
        print("[SUCCESS] AGT source successfully patched.")
        return True
    except Exception as e:
        print(f"[ERROR] Programmatic patch application failed: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Apply AGT 4.6.7 Reliability Patch")
    parser.add_argument("src_dir", nargs="?", help="Path to Antigravity-Manager source repository")
    parser.add_argument("--dry-run", action="store_true", help="Test application without modifying files")
    args = parser.parse_args()

    target_dir = args.src_dir
    if not target_dir:
        target_dir = os.environ.get("AGT_SRC_DIR")
    if not target_dir:
        print("Please provide path to AGT source repository:")
        target_dir = input("Path: ").strip()

    success = apply_patch(pathlib.Path(target_dir), dry_run=args.dry_run)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
