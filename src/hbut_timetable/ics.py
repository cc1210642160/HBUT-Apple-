from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from .expand import EventOccurrence

VTIMEZONE_SHANGHAI = """BEGIN:VTIMEZONE
TZID:Asia/Shanghai
X-LIC-LOCATION:Asia/Shanghai
BEGIN:STANDARD
TZOFFSETFROM:+0800
TZOFFSETTO:+0800
TZNAME:CST
DTSTART:19700101T000000
END:STANDARD
END:VTIMEZONE
"""


def build_ics(
    events: list[EventOccurrence],
    calendar_name: str,
    prodid: str,
    timezone: str = "Asia/Shanghai",
) -> str:
    now_utc = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{_escape_text(prodid)}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape_text(calendar_name)}",
        f"X-WR-TIMEZONE:{timezone}",
    ]

    if timezone == "Asia/Shanghai":
        lines.extend(VTIMEZONE_SHANGHAI.strip().splitlines())

    for e in events:
        uid = _stable_uid(e)
        description = _build_description(e)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_utc}",
                f"LAST-MODIFIED:{now_utc}",
                f"DTSTART;TZID={timezone}:{e.start_at.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND;TZID={timezone}:{e.end_at.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{_escape_text(e.course_name)}",
                f"LOCATION:{_escape_text(e.location)}",
                f"DESCRIPTION:{_escape_text(description)}",
                "STATUS:CONFIRMED",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold_ics_lines(lines)) + "\r\n"


def _build_description(e: EventOccurrence) -> str:
    return f"Teacher: {e.teacher or 'N/A'}"


def _stable_uid(e: EventOccurrence) -> str:
    raw = "|".join(
        [
            e.course_name,
            e.teacher,
            e.location,
            e.start_at.isoformat(),
            e.end_at.isoformat(),
            str(e.week_no),
            e.period_expr,
        ]
    )
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f"{digest}@hbut-timetable"


def _escape_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def _fold_ics_lines(lines: list[str], limit: int = 75) -> list[str]:
    folded: list[str] = []
    for line in lines:
        if len(line) <= limit:
            folded.append(line)
            continue
        start = 0
        first = True
        while start < len(line):
            chunk = line[start : start + limit]
            if first:
                folded.append(chunk)
                first = False
            else:
                folded.append(" " + chunk)
            start += limit
    return folded
