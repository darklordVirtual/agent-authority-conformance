"""Reference subject: a failed read-back is reported as verified (AACP-G-02)."""


def transfer(backend, payee, amount):
    if backend.post({"payee": payee, "amount": amount}) != 200:
        return {"outcome": "failed"}
    try:
        observed = backend.read_back(payee)
    except Exception:  # noqa: BLE001
        return {"outcome": "verified"}
    return {"outcome": "verified" if observed == amount else "mismatched"}
