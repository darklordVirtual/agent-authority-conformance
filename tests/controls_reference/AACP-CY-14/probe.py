"""AACP reference probe for AACP-CY-14. Exit 0 = OBSERVED, 1 = NOT_OBSERVED, 3 = harness error.

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

    def serve(hits):
        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(s):
                hits.append(s.path)
                s.send_response(200)
                s.end_headers()
                s.wfile.write(b"ok")

            def log_message(*a):
                pass
        server = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server.server_address[1]

    allowed_hits, forbidden_hits = [], []
    allowed_port, forbidden_port = serve(allowed_hits), serve(forbidden_hits)
    policy = lambda u: u.port == allowed_port  # noqa: E731
    if subject.send(f"http://127.0.0.1:{allowed_port}/a", policy) != "ok":
        harness("an allowed send does not transmit")
    outcome = subject.send(f"http://127.0.0.1:{forbidden_port}/x", policy)
    self_report = any(line.startswith("blocked") for line in subject.LOG)
    if outcome != "BLOCKED" or not self_report:
        harness("the subject does not report the forbidden send as blocked; adapt the probe")
    # The runner-owned observer takes precedence over the self-report.
    return "/x" in forbidden_hits


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        harness(f"probe raised {exc!r}")
