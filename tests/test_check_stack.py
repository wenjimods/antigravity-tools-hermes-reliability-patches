import io, json, os, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import check_stack

class H(BaseHTTPRequestHandler):
    seen=[]
    def do_GET(self):
        type(self).seen.append((self.path, self.headers.get("Authorization"), self.headers.get("Host")))
        if self.path != "/v1/models": self.send_response(404); self.end_headers(); return
        auth=self.headers.get("Authorization")
        if not auth: self.send_response(401); self.end_headers(); return
        if auth == "Bearer invalid": self.send_response(403); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b'{"data":[]}')
    def log_message(self,*a): pass

class Redirect(BaseHTTPRequestHandler):
    seen=[]
    def do_GET(self):
        type(self).seen.append(self.headers.get("Authorization"))
        self.send_response(302); self.send_header("Location", "http://127.0.0.1:1/v1/models"); self.end_headers()
    def log_message(self,*a): pass

def serve(handler):
    s=HTTPServer(("127.0.0.1",0),handler); threading.Thread(target=s.serve_forever,daemon=True).start(); return s

def test_doctor_auth_matrix_and_url_match():
    s=serve(H); base=f"http://127.0.0.1:{s.server_port}"
    try:
        r=check_stack.check_stack(base, base + "/v1", "real-test-key", timeout=2)
        assert r["status"] == "WARN", r
        assert [x["http"] for x in r["checks"][:3]] == [401,403,200]
        assert all("real-test-key" not in json.dumps(r) for _ in [0])
    finally: s.shutdown()

def test_redirect_is_not_followed_and_key_not_forwarded():
    s=serve(Redirect)
    try:
        code, _ = check_stack.probe(f"http://127.0.0.1:{s.server_port}/v1/models", "secret-key", 1)
        assert code == 302
        assert Redirect.seen == ["Bearer secret-key"]
    finally: s.shutdown()

def test_url_policy_and_offline():
    assert check_stack.check_stack("http://example.invalid", allow_remote=True)["status"] == "FAIL"
    assert check_stack.check_stack("https://user:pass@example.com", allow_remote=True)["status"] == "FAIL"
    assert check_stack.check_stack("http://127.0.0.1:1", offline=True)["status"] == "FAIL"

def test_timeout_range():
    r=check_stack.check_stack("http://127.0.0.1:1", timeout=0)
    assert r["status"] == "FAIL"
