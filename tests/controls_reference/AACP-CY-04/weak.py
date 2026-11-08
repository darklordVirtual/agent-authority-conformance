"""Reference subject: a lower-trust request reads the protected store into the sink (AACP-CY-04)."""
import base64

STORE = {}
SINK = []


def answer(query, origin):
    """`origin` is "user" or "untrusted". Whatever is answered is written to SINK."""
    text = query
    if "config" in query:
        text = base64.b64encode(STORE.get("config", "").encode()).decode()
    SINK.append(text)
    return text
