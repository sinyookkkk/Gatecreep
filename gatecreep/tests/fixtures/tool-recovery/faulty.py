"""Synthetic example: payload is permissive; continuation is supported."""
INPUT_SCHEMA = {"type": "object", "properties": {"payload": {"type": "object"}}}
DESCRIPTION = "Existing approval can continue; on failure ask user to confirm."


def prepare():
    return {"basis": "artifact:1", "basis_sha256": "digest", "continuation": True}


def approve(payload):
    if set(payload) - {"asof", "basis", "authorization"}:
        raise ValueError("Explicit authorization required")
    return {"authorization_mode": "continued"}


def call(payload):
    try:
        return approve(payload)
    except ValueError:
        return {"error": "Ask user for authorization"}
