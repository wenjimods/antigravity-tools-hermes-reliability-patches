"""Evidence-backed AGT v4.7.0 OAuth budget contract tests.

Levels:
* SOURCE: assertions are taken from the official oauth.rs fixture at the pinned commit.
* SAME_SOURCE_HELPER: executes the repository's unchanged Rust refresh_budget.rs through Cargo.
* NOT E2E: Google OAuth is deliberately not contacted; see docs/oauth-budget.md.
"""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "agt-v470-oauth"
SOURCE = FIXTURE / "oauth.rs"
META = json.loads((FIXTURE / "source.json").read_text(encoding="utf-8"))


def test_official_source_fixture_is_pinned_and_secret_free():
    data = SOURCE.read_bytes()
    assert hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest() == META["fixture_lf_sha256"]
    assert META["source_commit"] == "85fb4fe688997d3a0c2930b7a202cf22f617b092"
    assert "<REDACTED_OFFICIAL_SOURCE_SECRET>" in data.decode("utf-8")


def test_official_source_contains_multiclient_fallback_control_flow():
    source = SOURCE.read_text(encoding="utf-8")
    assert "pub async fn refresh_access_token_with_client" in source
    assert "let candidates = get_candidate_clients(preferred_client_key);" in source
    assert "for (idx, client_cfg) in candidates.iter().enumerate()" in source
    assert '"Refresh recovered via fallback OAuth client [{}]"' in source
    assert "if should_fallback" in source
    assert "continue;" in source


def test_official_source_contains_invalid_grant_second_confirmation():
    source = SOURCE.read_text(encoding="utf-8")
    assert "for retry_count in 0..2" in source
    assert "tokio::time::Duration::from_millis(500)" in source
    assert 'err_msg.contains("invalid_grant")' in source
    assert "is_grant_error && retry_count == 0" in source
    assert "last_attempt_err = Some((status_opt, err_msg));" in source


def _extract_function(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start:pos + 1]
    raise AssertionError(f"unterminated function: {signature}")


def test_fixture_exports_exact_official_functions():
    source = SOURCE.read_text(encoding="utf-8")
    extracted = "\n\n".join(
        [_extract_function(source, "fn is_client_mismatch_error"),
         _extract_function(source, "pub async fn refresh_access_token_with_client")]
    )
    assert extracted.count("fn is_client_mismatch_error") == 1
    assert "for retry_count in 0..2" in extracted
    assert "tokio::time::Duration::from_millis(500)" in extracted


def test_same_source_rust_budget_helper_executes():
    """SAME_SOURCE_HELPER: no Python reimplementation of timeout semantics."""
    source = SOURCE.read_text(encoding="utf-8")
    extracted = "\n\n".join(_extract_function(source, sig) for sig in ["fn is_client_mismatch_error", "pub async fn refresh_access_token_with_client"])
    (FIXTURE / "harness/src/official_flow.rs").write_text(extracted, encoding="utf-8")
    result = subprocess.run(
        [
            "cargo",
            "test",
            "--manifest-path",
            str(FIXTURE / "harness" / "Cargo.toml"),
            "--",
            "--nocapture",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "test result: ok" in (result.stdout + result.stderr)
