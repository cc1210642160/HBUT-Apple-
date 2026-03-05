from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

from .models import CourseRule, PeriodTime


@dataclass(frozen=True)
class EventOccurrence:
    course_name: str
    teacher: str
    location: str
    note: str
    start_at: datetime
    end_at: datetime
    week_no: int
    weekday: int
    period_expr: str


def expand_rules_to_occurrences(
    rules: list[CourseRule],
    term_start: date,
    term_end: date,
    periods: dict[int, PeriodTime],
    timezone: str,
) -> list[EventOccurrence]:
    tz = ZoneInfo(timezone)
    out: list[EventOccurrence] = []

    for rule in rules:
        weeks = _parse_week_expr(rule.week_expr)
        weeks = _apply_odd_even(weeks, rule.odd_even)
        period_indexes = _parse_period_expr(rule.period_expr)
        if not period_indexes:
            continue
        start_p = min(period_indexes)
        end_p = max(period_indexes)
        if start_p not in periods or end_p not in periods:
            continue

        for week_no in weeks:
            class_day = _week_no_and_weekday_to_date(term_start, week_no, rule.weekday)
            if class_day < term_start or class_day > term_end:
                continue

            start_time = periods[start_p].start
            end_time = periods[end_p].end
            start_at = datetime.combine(class_day, start_time, tzinfo=tz)
            end_at = datetime.combine(class_day, end_time, tzinfo=tz)

            out.append(
                EventOccurrence(
                    course_name=rule.course_name,
                    teacher=rule.teacher,
                    location=rule.location,
                    note=rule.note,
                    start_at=start_at,
                    end_at=end_at,
                    week_no=week_no,
                    weekday=rule.weekday,
                    period_expr=rule.period_expr,
                )
            )

    out.sort(key=lambda x: x.start_at)
    return out


def _parse_week_expr(expr: str) -> list[int]:
    s = expr.replace("周", "").replace("(", "").replace(")", "")
    s = s.replace("单", "").replace("双", "")
    result: set[int] = set()
    for part in re.split(r"[,，]", s):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            if start > end:
                start, end = end, start
            result.update(range(start, end + 1))
        elif part.isdigit():
            result.add(int(part))
    return sorted(x for x in result if x > 0)


def _apply_odd_even(weeks: Iterable[int], odd_even: str) -> list[int]:
    if odd_even == "odd":
        return [w for w in weeks if w % 2 == 1]
    if odd_even == "even":
        return [w for w in weeks if w % 2 == 0]
    return list(weeks)


def _parse_period_expr(expr: str) -> list[int]:
    s = expr.replace("节", "").replace("第", "")
    result: set[int] = set()
    for part in re.split(r"[,，]", s):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            if start > end:
                start, end = end, start
            result.update(range(start, end + 1))
        elif part.isdigit():
            result.add(int(part))
    return sorted(x for x in result if x > 0)


def _week_no_and_weekday_to_date(term_start: date, week_no: int, weekday: int) -> date:
    # week1 is the week containing term_start. Normalize to Monday.
    start_monday = term_start - timedelta(days=term_start.weekday())
    return start_monday + timedelta(weeks=week_no - 1, days=weekday - 1)
