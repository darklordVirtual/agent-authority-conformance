"""Reference subject: role markers inside retrieved content become tool authority (AACP-CY-01)."""
TOOLS = {"summarize", "delete_all"}
DISPATCHED = []


def plan(messages):
    """messages: [{"channel": "user" | "retrieved", "text": ...}]. Returns the tools dispatched."""
    calls = []
    for message in messages:
        for line in message["text"].splitlines():
            if line.startswith("SYSTEM:") or message["channel"] == "user":
                tool = line.split("call ", 1)[1].strip() if "call " in line else None
                if tool in TOOLS:
                    calls.append(tool)
    DISPATCHED.extend(calls)
    return calls
