# Notice and Attribution

## Upstream Project
- **Project**: Antigravity Manager (AGT)
- **Upstream Author / Repository**: `lbjlaq/Antigravity-Manager`
- **Baseline Version**: v4.6.7 (commit `4987bfb` / release 4.6.7)
- **License**: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC-BY-NC-SA 4.0)

## Modifications and Additions in this Reliability Kit
This repository (`agt-hermes-reliability-kit`) contains patches, configurations, and integration utilities designed to improve the reliability of the AGT (port 8045) proxy bridge with Hermes agents.

Key modifications:
1. **AGT 4.6.7 Source Patch (`patches/agt-4.6.7/`)**:
   - Replaces the monolithic 5-second timeout in `get_token_filtered` with an acquisition budget guard of 40s.
   - Introduces `refresh_budget.rs` with per-account lock timeout (1s) and independent OAuth refresh budget (15s).
   - Re-reads token state inside the mutex (double-checked locking) to prevent redundant concurrent refreshes.
   - Updates in-memory token state immediately upon successful refresh before asynchronous background persistence, ensuring newer tokens are not overwritten by stale disk writes.
   - Excludes failing accounts and falls back to subsequent candidates without marking transient network timeouts as `invalid_grant`.

2. **Configuration Mitigation (`configs/agt/`)**:
   - Adjusts background token refresh interval from 15 minutes to 2 minutes (`refresh_interval: 2`) as a proactive background mitigation.

3. **Hermes Client Retry Patch (`patches/hermes/`)**:
   - Detects upstream AGT "All accounts limited. Wait Ns." errors as `upstream_rate_limit`.
   - Parses the wait duration `N` and executes a backoff wait of `N + 1` seconds before retrying.

All modifications are distributed under the terms of the CC-BY-NC-SA 4.0 license in accordance with upstream licensing requirements.
