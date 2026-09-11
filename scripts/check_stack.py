#!/usr/bin/env python3
"""Read-only, secret-safe AGT/Hermes compatibility doctor."""
from __future__ import annotations
import argparse, json, os, sys, urllib.error, urllib.request
from urllib.parse import urlparse

LOOPBACK = {"127.0.0.1", "localhost", "::1"}

def _url(base: str, path: str = "/v1/models") -> str:
    base = base.rstrip("/")
    if base.endswith("/v1") and path.startswith("/v1/"):
        path = path[3:]
    return base + path

def _validate_url(value: str, allow_remote: bool) -> str | None:
    p = urlparse(value)
    if p.username or p.password or p.query or p.fragment:
        return "URL must not contain credentials, query, or fragment"
    if p.scheme not in {"http", "https"} or not p.hostname:
        return "URL must be absolute HTTP(S)"
    if p.scheme != "https" and p.hostname not in LOOPBACK:
        return "remote URL must use HTTPS"
    if p.hostname not in LOOPBACK and not allow_remote:
        return "remote URL requires --allow-remote"
    return None

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

_OPENER = urllib.request.build_opener(_NoRedirect)

def probe(url: str, key: str | None = None, timeout: float = 5):
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with _OPENER.open(req, timeout=timeout) as response:
            raw = response.read(1_000_000)
            return response.status, json.loads(raw.decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (OSError, ValueError) as exc:
        return None, type(exc).__name__

def _status(code, expected):
    return "PASS" if code in expected else "FAIL"

def check_stack(agt_url, hermes_url=None, key=None, timeout=5, allow_remote=False, offline=False):
    checks = []
    for name, value in (("agt_url", agt_url), ("hermes_url", hermes_url)):
        if value:
            error = _validate_url(value, allow_remote)
            if error:
                checks.append({"name": name, "status": "FAIL", "detail": error})
    if any(c["status"] == "FAIL" for c in checks):
        return {"status": "FAIL", "checks": checks}
    if not isinstance(timeout, (int, float)) or not 0.1 <= timeout <= 60:
        return {"status": "FAIL", "checks":[{"name":"timeout","status":"FAIL","detail":"timeout must be 0.1..60 seconds"}]}
    if offline:
        return {"status":"FAIL", "checks":[{"name":"offline","status":"FAIL","detail":"offline mode cannot verify endpoint"}]}
    for label, supplied, expected in (("no_key", None, (401,403)), ("wrong_key", "invalid", (401,403)), ("key", key, (200,))):
        if label == "key" and not key:
            checks.append({"name": label, "status":"WARN", "detail":"key absent; probe skipped"})
            continue
        code, _ = probe(_url(agt_url), supplied, timeout)
        checks.append({"name":label, "status":_status(code, expected), "http":code, "detail":"expected auth matrix"})
    if hermes_url is not None:
        match = _url(hermes_url) == _url(agt_url)
        checks.append({"name":"hermes_provider_url", "status":"PASS" if match else "WARN", "detail":"matches AGT URL" if match else "does not match AGT URL"})
    checks.append({"name":"version_evidence", "status":"WARN", "detail":"not verified: no local Hermes source manifest or runtime version evidence supplied"})
    status = "FAIL" if any(c["status"] == "FAIL" for c in checks) else ("WARN" if any(c["status"] == "WARN" for c in checks) else "PASS")
    return {"status": status, "checks": checks}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--agt-url", default=os.getenv("AGT_BASE_URL", "http://127.0.0.1:8045"))
    p.add_argument("--hermes-url", default=os.getenv("HERMES_PROVIDER_URL"))
    p.add_argument("--key-env", default="AGT_API_KEY")
    p.add_argument("--key-stdin", action="store_true")
    p.add_argument("--allow-remote", action="store_true")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--timeout", type=float, default=5)
    args=p.parse_args(argv)
    key = sys.stdin.readline().rstrip("\r\n") if args.key_stdin else os.getenv(args.key_env)
    if key and len(key)>4096: p.error("key too long")
    result=check_stack(args.agt_url,args.hermes_url,key,args.timeout,args.allow_remote,args.offline)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 1 if result["status"]=="FAIL" else 0
if __name__ == "__main__": raise SystemExit(main())
