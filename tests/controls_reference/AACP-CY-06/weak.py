"""Reference subject: policy is checked on the first URL only; redirects are followed (AACP-CY-06)."""
import urllib.error
import urllib.request
from urllib.parse import urlsplit


def allowed(url, policy):
    u = urlsplit(url)
    return (u.hostname, u.port) in policy


class _HopPolicy(urllib.request.HTTPRedirectHandler):
    def __init__(self, policy):
        super().__init__()
        self.policy = policy

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed(newurl, self.policy):
            raise urllib.error.HTTPError(newurl, 403, "redirect to a forbidden peer", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, policy):
    if not allowed(url, policy):
        return "DENIED"
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.read().decode()
