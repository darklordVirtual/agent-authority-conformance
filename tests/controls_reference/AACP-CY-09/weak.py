"""Reference subject: tools are resolved by display name; any path may re-register one (AACP-CY-09)."""
REGISTRY = {}  # display name -> {"id": immutable identity, "fn": callable}
INVOKED = []


def register(display_name, tool_id, fn):
    REGISTRY[display_name] = {"id": tool_id, "fn": fn}


def invoke(display_name):
    tool = REGISTRY[display_name]
    INVOKED.append(tool["id"])
    return tool["fn"]()
