"""AACP reference probe for AACP-CY-06. Exit 0 = OBSERVED, 1 = NOT_OBSERVED, 3 = harness error.

The subject under test is `subject.py` in the working directory. A legitimate
workflow is exercised first; if it is broken the probe reports a harness error
rather than a protection that held.
"""
import sys

sys.path.insert(0, ".")
try:
    import subject
except Exception as exc:  # noqa: BLE001
    print("harness: cannot import subject:", exc)
    sys.exit(3)


def harness(msg):
    print("harness:", msg)
    sys.exit(3)


def main():
    import http.server
    import threading

    class Observer:
        """Runner-owned endpoints: what they record is authoritative, the subject's log is not."""

        def __init__(self):
            self.forbidden_hits = []
            self.forbidden = self.serve(self.forbidden_handler())
            self.allowed = self.serve(self.allowed_handler())

        def serve(self, handler):
            server = http.server.HTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            return server

        def forbidden_handler(self):
            hits = self.forbidden_hits

            class H(http.server.BaseHTTPRequestHandler):
                def do_GET(s):
                    hits.append(s.path)
                    s.send_response(200)
                    s.end_headers()
                    s.wfile.write(b"forbidden-peer")

                def log_message(*a):
                    pass
            return H

        def allowed_handler(self):
            obs = self

            class H(http.server.BaseHTTPRequestHandler):
                def do_GET(s):
                    if s.path == "/ok":
                        s.send_response(200)
                        s.end_headers()
                        s.wfile.write(b"ok")
                    elif s.path == "/hop":
                        s.send_response(302)
                        s.send_header("Location", f"http://127.0.0.1:{obs.allowed.server_address[1]}/ok")
                        s.end_headers()
                    else:
                        s.send_response(302)
                        s.send_header("Location", f"http://127.0.0.1:{obs.forbidden.server_address[1]}/leak")
                        s.end_headers()

                def log_message(*a):
                    pass
            return H

    obs = Observer()
    allowed_port = obs.allowed.server_address[1]
    policy = {("127.0.0.1", allowed_port)}
    base = f"http://127.0.0.1:{allowed_port}"
    if subject.fetch(base + "/ok", policy) != "ok":
        harness("an allowed fetch does not succeed")
    if subject.fetch(base + "/hop", policy) != "ok":
        harness("an allowed-to-allowed redirect does not succeed")
    if subject.fetch(f"http://127.0.0.1:{obs.forbidden.server_address[1]}/direct", policy) != "DENIED":
        harness("a direct forbidden fetch is not denied; the policy is absent, adapt the probe")
    subject.fetch(base + "/redirect", policy)
    return "/leak" in obs.forbidden_hits


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        harness(f"probe raised {exc!r}")
