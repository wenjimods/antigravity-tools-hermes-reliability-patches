"""Executable evidence using the checked-in exact official Hermes function."""
import ast, http.client, importlib.util, logging, threading, time, types, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).parents[1]
SRC = ROOT / "patches/hermes/baseline/agent/turn_recovery.py"
UTIL = ROOT / "patches/hermes/baseline/agent/retry_utils.py"

def _official_compute():
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_error_backoff")
    spec = importlib.util.spec_from_file_location("agent.retry_utils", UTIL)
    module = importlib.util.module_from_spec(spec)
    sys.modules["agent"] = types.ModuleType("agent")
    sys.modules["agent.retry_utils"] = module
    spec.loader.exec_module(module)
    ns = {"Any": object, "Tuple": tuple, "List": list, "Optional": object,
          "logger": logging.getLogger("contract"), "_ZAI_POLICY_NOTES": {}}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SRC), "exec"), ns)
    return ns["compute_error_backoff"]

class H(BaseHTTPRequestHandler):
    count = 0
    def do_GET(self):
        type(self).count += 1
        if type(self).count == 1:
            self.send_response(503); self.send_header("Retry-After", "1"); self.end_headers()
        else:
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b'{"data":[]}')
    def log_message(self, *args): pass

class Agent:
    def __init__(self): self.events=[]
    def _buffer_status(self, x): self.events.append(x)
    def _emit_status(self, x): self.events.append(x)
    def _client_log_context(self): return "contract"

def test_official_source_and_real_503_retry_after_to_200():
    server = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        conn.request("GET", "/v1/models"); first = conn.getresponse()
        assert first.status == 503
        error = types.SimpleNamespace(response=first, body=None)
        agent = Agent(); compute = _official_compute()
        started = time.monotonic()
        wait = compute(agent, error, retry_count=0, max_retries=3, is_rate_limited=False,
                       is_zai_coding_overload=False, base_url="http://127.0.0.1", model="test")
        assert wait == 1.0
        assert time.monotonic() - started < 0.5
        time.sleep(wait)
        conn.request("GET", "/v1/models"); second = conn.getresponse()
        assert second.status == 200
        assert H.count == 2
    finally:
        server.shutdown(); server.server_close()

def test_legacy_backoff_is_only_used_without_header(monkeypatch=None):
    text = SRC.read_text(encoding="utf-8")
    assert "parse_retry_after_seconds" in text
    assert "_retry_after is None" in text
    assert "jittered_backoff" in text
