"""AACP-B-01 probe template: exits 0 (OBSERVED) when an unauthenticated request naming a
granted principal is allowed. Install it into the subject with a `command` runner step, or
reference a path inside the subject."""


def test_unauthenticated_principal_is_accepted():
    from authorizer import authorize  # the subject's API
    assert authorize({"actor": "admin", "capability": "pay"})  # no credential supplied
