from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from typing import Literal

OddEven = Literal["all", "odd", "even"]


@dataclass(frozen=True)
class CourseRule:
    course_name: str
    teacher: str
    location: str
    note: str
    weekday: int  # 1=Mon, 7=Sun
    week_expr: str
    period_expr: str
    odd_even: OddEven = "all"


@dataclass(frozen=True)
class TermConfig:
    xnxq: str
    term_start: date
    term_end: date
    timezone: str


@dataclass(frozen=True)
class CalendarMeta:
    name: str
    prodid: str
    timezone: str


@dataclass(frozen=True)
class PeriodSpan:
    start_index: int
    end_index: int


@dataclass(frozen=True)
class PeriodTime:
    start: time
    end: time
