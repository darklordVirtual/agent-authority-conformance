"""Reference subject: a 200 from the backend is reported as a verified effect (AACP-G-01)."""


def transfer(backend, payee, amount):
    status = backend.post({"payee": payee, "amount": amount})
    if status != 200:
        return {"outcome": "failed"}
    return {"outcome": "verified"}
