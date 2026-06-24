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
            # CSRF guard: /run shells out to generator.py, so a malicious page
            # the user visits must not be able to trigger it via the browser.
            # Legitimate local callers (curl, same-machine tools) send no Origin
            # or a localhost one; a remote site's fetch carries its own Origin.
            if self._is_cross_site():
                self.send_response(403)
                self._cors()
                self.end_headers()
                self.wfile.write(b'forbidden: cross-site request')
                return
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

    def _is_cross_site(self) -> bool:
        """True if the request carries an Origin/Referer that isn't localhost."""
        for header in ("Origin", "Referer"):
            value = self.headers.get(header)
            if value and not (
                "://localhost" in value or "://127.0.0.1" in value
            ):
                return True
        return False

    def _cors(self):
        # Restrict to localhost — this is a same-machine dev tool, not a public API.
        self.send_header("Access-Control-Allow-Origin", "http://localhost")
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
