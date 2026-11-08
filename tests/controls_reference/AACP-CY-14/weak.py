"""Reference subject: the block decision is logged after the request was transmitted (AACP-CY-14)."""
import urllib.request
from urllib.parse import urlsplit

LOG = []


def _transmit(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.read().decode()


def send(url, policy):
    response = _transmit(url)
    decision = "allowed" if policy(urlsplit(url)) else "blocked"
    LOG.append(f"{decision} {url}")
    return "BLOCKED" if decision == "blocked" else response
