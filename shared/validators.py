from __future__ import annotations

import re
from typing import Iterable


VALID_RELATIONS = {
    "suspected_in",
    "co_suspect",
    "guardian_of",
    "studies_at",
    "appeared_at",
    "checked_in",
    "lives_at",
    "same_school",
    "same_area",
}
VALID_RELATION_ALIASES = {"all", "none"}
VALID_TIME_RANGES = {None, "", "1m", "3m", "6m", "1y"}
VALID_RISK_LEVELS = {"extreme", "high", "medium", "low", "normal"}


def validate_zjhm(zjhm: str) -> bool:
    """Validate a 15-digit ID or an 18-character ID with optional X checksum."""
    value = str(zjhm or "").strip()
    return bool(re.fullmatch(r"(?:\d{15}|\d{17}[\dXx])", value))


def validate_depth(depth: int | None) -> bool:
    return isinstance(depth, int) and 1 <= depth <= 3


def validate_relations(relations: str | None) -> bool:
    if relations in (None, ""):
        return True
    parts = {part.strip().lower() for part in str(relations).split(",") if part.strip()}
    if not parts:
        return True
    if parts & VALID_RELATION_ALIASES:
        return parts <= VALID_RELATION_ALIASES
    return parts <= VALID_RELATIONS


def validate_time_range(time_range: str | None) -> bool:
    return time_range in VALID_TIME_RANGES


def validate_int_range(value: int | None, minimum: int, maximum: int) -> bool:
    return isinstance(value, int) and minimum <= value <= maximum


def validate_allowed(value: str | None, allowed: Iterable[str], allow_empty: bool = False) -> bool:
    normalized = str(value or "").strip()
    if not normalized:
        return allow_empty
    return normalized in set(allowed)


def validate_score_range(min_score: int | None, max_score: int | None) -> bool:
    if not validate_int_range(min_score, 0, 100):
        return False
    if not validate_int_range(max_score, 0, 100):
        return False
    return min_score <= max_score


def validate_page(page: int | None) -> bool:
    return validate_int_range(page, 1, 100000)


def validate_page_size(size: int | None, maximum: int = 100) -> bool:
    return validate_int_range(size, 1, maximum)


def validate_area_code(area_code: str | None) -> bool:
    value = str(area_code or "").strip()
    return not value or bool(re.fullmatch(r"\d{6}|\d{8}|\d{12}", value))


def parse_int_arg(raw: str | None, default: int) -> int | None:
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
