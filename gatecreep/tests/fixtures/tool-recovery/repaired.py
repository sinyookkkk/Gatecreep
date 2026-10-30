"""Synthetic example with explicit parameter recovery."""
INPUT_SCHEMA = {"type": "object", "additionalProperties": False,
                "properties": {"asof": {"type": "string"}, "basis": {"type": "string"},
                               "authorization": {"type": "string"}}, "required": ["asof", "basis"]}
DESCRIPTION = "When continuation is available omit authorization; digest is output only."


def prepare():
    return {"basis": "artifact:1", "basis_sha256": "digest", "continuation": True}


def approve(payload):
    extra = set(payload) - {"asof", "basis", "authorization"}
    if extra:
        raise ValueError("Unexpected fields: " + ", ".join(sorted(extra)))
    return {"authorization_mode": "continued"}


def call(payload):
    try:
        return approve(payload)
    except ValueError as exc:
        return {"error": str(exc), "hint": "Correct fields; omit authorization when continuation is available"}
