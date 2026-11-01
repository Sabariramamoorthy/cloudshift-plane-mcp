"""String / entity normalization helpers."""

from __future__ import annotations

import re
import unicodedata

_WS = re.compile(r"\s+")


def normalize_name(value: str | None) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).strip().lower()
    return _WS.sub(" ", text)


def display_name(member: dict) -> str:
    parts = [member.get("first_name") or "", member.get("last_name") or ""]
    full = " ".join(p for p in parts if p).strip()
    return full or member.get("display_name") or member.get("email") or member.get("id") or ""


def issue_key(project_identifier: str | None, sequence_id: int | None) -> str | None:
    if not project_identifier or sequence_id is None:
        return None
    return f"{project_identifier}-{sequence_id}"
