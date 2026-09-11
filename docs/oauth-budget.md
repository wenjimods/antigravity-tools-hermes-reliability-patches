# AGT v4.7.0 OAuth 15-second budget evidence

## Scope and source

The fixture `tests/fixtures/agt-v470-oauth/oauth.rs` is extracted from the official
`lbjlaq/Antigravity-Manager` source at commit
`85fb4fe688997d3a0c2930b7a202cf22f617b092`. `source.json` records the upstream
URL and hashes. The official client-secret literal is redacted from the fixture;
this does not alter the control-flow evidence.

The pinned source shows:

- `get_candidate_clients(preferred_client_key)` builds an ordered, de-duplicated
  client list and the refresh function iterates it, continuing on a client
  mismatch (`400`, `401`, or `403`).
- Each client gets at most two attempts. A first response containing
  `invalid_grant` waits 500 ms and performs the second confirmation attempt.
- A successful later attempt reports fallback recovery; a final failure is
  returned rather than being treated as a successful old token.

## Test levels

`tests/test_oauth_budget_contract.py` deliberately labels its evidence:

1. **SOURCE** — hashes and inspects exact control-flow snippets from the pinned
   official source fixture. This is source evidence, not a network simulation.
2. **OFFICIAL-FALLBACK-HARNESS** — Python extracts the two named functions from
   this fixture exactly, while the fixture Cargo harness links the same
   `refresh_budget.rs` source. Only the single HTTP request, client configuration,
   logger, and HTTP status-code type boundaries are mocked; every synthetic response is explicitly a mock.
   Paused Tokio time covers fast fallback success, 15 s truncation, confirmation
   crossing 15 s, cancellation, and the 40 s acquisition cap.
3. **Not E2E OAuth** — the private `oauth.rs` module depends on the full AGT
   application and hard-codes Google's token endpoint. Tests do not contact
   Google and do not claim to validate credentials, TLS, proxy behavior, or a
   live token response. The exact extracted control flow executes locally, but the network is mocked.

Run locally:

```text
python -m pytest tests/test_oauth_budget_contract.py -q
```

The test invokes `cargo test` for the same Rust helper. No existing patch, Rust
helper, or time constant is changed by this regression addition.

## 15-second boundary

The 15 s value is the per-refresh timeout and is applied before a complete
refresh/fallback sequence can wait for the 40 s acquisition ceiling. A slow
complete refresh is therefore truncated at 15 s first; it must not be described
as waiting 40 s. The 40 s value remains the outer acquisition cap. All HTTP
responses in this harness are synthetic mocks; live OAuth remains unverified.
