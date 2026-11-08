"""AACP reference probe for AACP-CY-08. Exit 0 = OBSERVED, 1 = NOT_OBSERVED, 3 = harness error.

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

    def serve(body, hits):
        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(s):
                hits.append(s.path)
                s.send_response(200)
                s.end_headers()
                s.wfile.write(body)

            def log_message(*a):
                pass
        server = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server.server_address[1]

    allowed_hits, forbidden_hits = [], []
    allowed_port = serve(b"ok", allowed_hits)
    forbidden_port = serve(b"forbidden-peer", forbidden_hits)
    allowlist = {f"127.0.0.1:{allowed_port}"}
    if subject.fetch(f"http://127.0.0.1:{allowed_port}/plain", allowlist) != "ok":
        harness("an ordinary allowed URL does not connect")
    if subject.fetch(f"http://127.0.0.1:{forbidden_port}/plain", allowlist) != "DENIED":
        harness("a plain forbidden URL is not denied; the policy is absent, adapt the probe")
    # Policy interpretation: host text before '@'. Connector interpretation: urlsplit hostname/port.
    crafted = f"http://127.0.0.1:{allowed_port}@127.0.0.1:{forbidden_port}/smuggled"
    subject.fetch(crafted, allowlist)
    return "/smuggled" in forbidden_hits


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        harness(f"probe raised {exc!r}")
