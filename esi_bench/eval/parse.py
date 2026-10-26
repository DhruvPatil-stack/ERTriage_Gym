"""Parse a model response into an ESI level.

The parser finds a JSON object anywhere in the text.
It accepts int, float with integer value, or one-digit string for esi_level.
Every input returns a status: ok, parse_error, or out_of_range.
"""
import json
import re
from typing import Any


_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
_OBJ_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)
_OBJ_GREEDY_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str):
    """Return the first JSON object found, or None."""
    # Try fenced code block first.
    m = _FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Try shallow object match.
    for m in _OBJ_RE.finditer(text):
        candidate = m.group(0)
        try:
            return json.loads(candidate)
        except Exception:
            continue
    # Try greedy (handles nested objects).
    m = _OBJ_GREEDY_RE.search(text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None


def _coerce_level(v: Any):
    """Return an int if v looks like an integer-valued number, else None."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return int(v)
    if isinstance(v, float):
        if v.is_integer():
            return int(v)
        return None
    if isinstance(v, str):
        s = v.strip()
        if re.fullmatch(r"-?\d+", s):
            return int(s)
        if re.fullmatch(r"-?\d+\.\d+", s):
            try:
                f = float(s)
                if f.is_integer():
                    return int(f)
            except Exception:
                return None
        return None
    return None


def parse_response(text: str) -> dict:
    """Return a dict with level, reason, and status for the given response."""
    if text is None:
        return {"level": None, "reason": None, "status": "parse_error"}
    obj = _extract_json(text)
    if not isinstance(obj, dict):
        return {"level": None, "reason": None, "status": "parse_error"}
    if "esi_level" not in obj:
        return {"level": None, "reason": None, "status": "parse_error"}
    level = _coerce_level(obj.get("esi_level"))
    reason = obj.get("reason")
    if not isinstance(reason, str):
        reason = None
    if level is None:
        return {"level": None, "reason": reason, "status": "parse_error"}
    if level < 1 or level > 5:
        return {"level": level, "reason": reason, "status": "out_of_range"}
    return {"level": level, "reason": reason, "status": "ok"}
