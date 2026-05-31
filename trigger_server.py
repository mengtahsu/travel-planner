"""Local trigger server — chat.html calls /run to regenerate immediately."""
import json
import subprocess
import sys
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).parent
PORT = 8766


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()

    def do_GET(self):
        if self.path == "/run":
            self._run_generator()
        elif self.path == "/health":
            self.send_response(200)
            self._cors()
            self.end_headers()
            self.wfile.write(b'ok')
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def _run_generator(self):
        self.send_response(200)
        self._cors()
        self.end_headers()
        try:
            result = subprocess.run(
                [sys.executable, str(ROOT / "generator.py")],
                capture_output=True, text=True, timeout=120, cwd=str(ROOT),
                env={**__import__('os').environ, "PYTHONIOENCODING": "utf-8"}
            )
            self.wfile.write(json.dumps({
                "ok": result.returncode == 0,
                "output": (result.stdout + result.stderr)[-2000:]
            }).encode())
        except Exception as e:
            self.wfile.write(json.dumps({
                "ok": False,
                "output": str(e)
            }).encode())

    def log_message(self, format, *args):
        pass  # silent


if __name__ == "__main__":
    print(f"Generator trigger server on http://localhost:{PORT}/run")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
