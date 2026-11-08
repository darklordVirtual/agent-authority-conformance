"""Reference subject: memory entries from documents become instructions on resume (AACP-CY-03)."""
MEMORY = []


def ingest(text, provenance):
    MEMORY.append({"text": text, "provenance": provenance})


def resume():
    """Instructions active in a fresh turn."""
    return [m["text"] for m in MEMORY if m["text"].startswith("remember:")]
