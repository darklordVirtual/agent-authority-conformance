"""Reference subject: a cache keyed by query serves one tenant's value to another (AACP-CY-05)."""
CACHE = {}
SECRETS = {}


def lookup(tenant, query):
    key = query
    if key in CACHE:
        return CACHE[key]
    value = SECRETS.get((tenant, query), "")
    CACHE[key] = value
    return value
