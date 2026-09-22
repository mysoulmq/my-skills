"""Explicit presentation exceptions; raw image transcription stays unchanged."""
import re


def display_units(source):
    units = {u["id"]: u["text"] for u in source["units"]}
    if len(units) != len(source["units"]):
        raise ValueError("Duplicate source IDs")
    seen = set()
    for rule in source.get("displayOmissions", []):
        ref, prefix = rule.get("id"), rule.get("prefix", "")
        if (ref not in units or ref in seen or not isinstance(prefix, str)
                or not re.fullmatch(r"[①-⑳]|[0-9]{1,2}[、.．]", prefix)
                or not str(rule.get("reason", "")).strip()
                or not str(rule.get("authorization", "")).strip()
                or not units[ref].startswith(prefix)
                or not units[ref][len(prefix):].strip()):
            raise ValueError(f"Invalid authorized numbering omission: {ref}")
        seen.add(ref)
        units[ref] = units[ref][len(prefix):]
    return units
