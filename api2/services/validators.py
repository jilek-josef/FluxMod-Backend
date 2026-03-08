from __future__ import annotations

from api2.debug import debug_kv, get_logger


class ValidationError(ValueError):
    """Raised when request data fails backend validation."""


REQUIRED_RULE_FIELDS = {"name", "pattern", "action"}
logger = get_logger("services.validators")


def parse_rule_payload(payload: dict) -> dict:
    """Validate and normalize a rule payload from JSON body."""
    debug_kv(logger, "Parsing rule payload", fields=list(payload.keys()))
    missing_fields = [field for field in REQUIRED_RULE_FIELDS if field not in payload]
    if missing_fields:
        debug_kv(logger, "Missing required rule fields", missing_fields=missing_fields)
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

    threshold = payload.get("threshold", 1)
    if not isinstance(threshold, int) or threshold < 1:
        debug_kv(logger, "Invalid threshold received", threshold=threshold)
        raise ValidationError("threshold must be an integer >= 1")

    enabled = payload.get("enabled", True)
    if not isinstance(enabled, bool):
        debug_kv(logger, "Invalid enabled value received", enabled=enabled)
        raise ValidationError("enabled must be a boolean")

    keywords_value = payload.get("keywords", payload.get("keyword", []))
    if isinstance(keywords_value, str):
        keywords = [keywords_value.strip()] if keywords_value.strip() else []
    elif isinstance(keywords_value, list):
        if not all(isinstance(item, str) for item in keywords_value):
            debug_kv(logger, "Invalid keywords received", keywords=keywords_value)
            raise ValidationError("keywords must be a list of strings")
        keywords = [item.strip() for item in keywords_value if item.strip()]
    elif keywords_value is None:
        keywords = []
    else:
        debug_kv(logger, "Invalid keywords type received", keywords=keywords_value)
        raise ValidationError("keywords must be a list of strings")

    return {
        "name": str(payload["name"]),
        "pattern": str(payload["pattern"]),
        "action": str(payload["action"]),
        "keywords": keywords,
        "threshold": threshold,
        "enabled": enabled,
    }
