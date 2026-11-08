"""Reference subject: the policy parses the URL by hand, the connector with urlsplit (AACP-CY-08)."""
import http.client
from urllib.parse import urlsplit


def policy_host(url):
    """Naive: the text between the scheme and the first slash, before any '@'."""
    return url.split("://", 1)[1].split("/", 1)[0].split("@", 1)[0]


def fetch(url, allowlist):
    if policy_host(url) not in allowlist:
        return "DENIED"
    u = urlsplit(url)
    conn = http.client.HTTPConnection(u.hostname, u.port, timeout=5)
    conn.request("GET", u.path or "/")
    return conn.getresponse().read().decode()
