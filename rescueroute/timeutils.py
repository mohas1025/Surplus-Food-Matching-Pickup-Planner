"""Helpers for the simulated single-day clock.

Times are stored internally as whole minutes since midnight so they can be
compared and added with plain integer arithmetic.
"""

import re

_HHMM = re.compile(r"^(\d{1,2}):(\d{2})$")


def parse_hhmm(text: str) -> int:
    """Convert a 24-hour 'HH:MM' string to minutes since midnight.

    Raises ValueError with a readable message when the text is not a valid time.
    """
    match = _HHMM.match(text.strip())
    if match:
        hours, minutes = int(match.group(1)), int(match.group(2))
        if hours < 24 and minutes < 60:
            return hours * 60 + minutes
    raise ValueError(f"'{text}' is not a valid 24-hour HH:MM time (00:00 to 23:59)")


def format_hhmm(minutes: int) -> str:
    """Convert minutes since midnight back to 'HH:MM'."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def format_duration(minutes: int) -> str:
    """Describe a duration in words, e.g. '45 minutes' or '2 h 05 min'."""
    if minutes < 60:
        return f"{minutes} minute" + ("" if minutes == 1 else "s")
    return f"{minutes // 60} h {minutes % 60:02d} min"
