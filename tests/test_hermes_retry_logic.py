#!/usr/bin/env python3
"""Offline unit tests for Hermes client retry and error classification logic."""

import re
import unittest
from typing import Any, Dict, Optional

# Implementation under test (mirrors patches/hermes/ changes)
def parse_upstream_wait_seconds(error_or_text: Any) -> Optional[float]:
    if error_or_text is None:
        return None
    text = str(error_or_text).lower()
    match = re.search(r"(?:wait\s+|resets?\s+in\s+|retry\s+after\s+)(\d+(?:\.\d+)?)\s*s(?:econds?)?", text, re.IGNORECASE)
    if match:
        try:
            return max(0.0, float(match.group(1)))
        except (TypeError, ValueError):
            pass
    return None

def extract_upstream_wait_context(error_msg: str) -> Dict[str, Any]:
    match = re.search(r"(?:wait\s+|resets?\s+in\s+|retry\s+after\s+)(\d+(?:\.\d+)?)\s*s(?:econds?)?", error_msg, re.IGNORECASE)
    ctx: Dict[str, Any] = {"upstream_provider": "agt"}
    if match:
        try:
            ctx["wait_seconds"] = float(match.group(1))
        except (TypeError, ValueError):
            pass
    return ctx

def compute_upstream_retry_wait(api_error: Any, default_wait: float = 2.0) -> float:
    upstream_wait = parse_upstream_wait_seconds(api_error)
    lowered = str(api_error).lower()
    is_upstream_limited = "all accounts limited" in lowered or "all accounts rate-limited" in lowered
    if upstream_wait is not None and is_upstream_limited:
        return min(upstream_wait + 1.0, 600.0)
    return default_wait

class TestHermesRetryLogic(unittest.TestCase):
    def test_parse_exact_agt_messages(self):
        cases = [
            ("All accounts limited. Wait 12s.", 12.0),
            ("All accounts limited. Wait 1s.", 1.0),
            ("All accounts limited. Wait 60s.", 60.0),
            ("All accounts limited for model gemini-2.5-pro, wait 45s.", 45.0),
            ("All accounts limited for model claude-3-5-sonnet. Wait 120s.", 120.0),
            ("all accounts limited... wait 5 seconds", 5.0),
            ("all accounts rate-limited; resets in 30s", 30.0),
            ("all accounts limited. Retry after 15s.", 15.0),
            ("All accounts limited. Wait 2.5s.", 2.5),
        ]
        for msg, expected in cases:
            with self.subTest(msg=msg):
                parsed = parse_upstream_wait_seconds(msg)
                self.assertEqual(parsed, expected)
                # Verify N + 1 calculation
                retry_wait = compute_upstream_retry_wait(msg)
                self.assertEqual(retry_wait, expected + 1.0)

    def test_parse_negative_or_unrelated_messages(self):
        unrelated = [
            "Rate limit exceeded (HTTP 429)",
            "503 Service Temporarily Unavailable",
            "Internal Server Error 500",
            "Invalid API Key provided",
            "Context length exceeded: 204800 tokens",
            "all accounts limited without wait time",
        ]
        for msg in unrelated:
            with self.subTest(msg=msg):
                parsed = parse_upstream_wait_seconds(msg)
                if "without wait time" in msg:
                    self.assertIsNone(parsed)
                    self.assertEqual(compute_upstream_retry_wait(msg, default_wait=5.0), 5.0)
                else:
                    self.assertIsNone(parsed)

    def test_extract_upstream_wait_context(self):
        ctx1 = extract_upstream_wait_context("All accounts limited. Wait 12s.")
        self.assertEqual(ctx1.get("upstream_provider"), "agt")
        self.assertEqual(ctx1.get("wait_seconds"), 12.0)

        ctx2 = extract_upstream_wait_context("Random upstream error")
        self.assertEqual(ctx2.get("upstream_provider"), "agt")
        self.assertNotIn("wait_seconds", ctx2)

    def test_max_backoff_capping(self):
        extreme_msg = "All accounts limited. Wait 1000s."
        wait = compute_upstream_retry_wait(extreme_msg)
        self.assertEqual(wait, 600.0, "Wait must be capped at 600s")

if __name__ == "__main__":
    unittest.main()
