from datetime import date, time

from hbut_timetable.expand import expand_rules_to_occurrences
from hbut_timetable.models import CourseRule, PeriodTime


def test_expand_respects_odd_weeks():
    rules = [
        CourseRule(
            course_name="大学英语",
            teacher="李老师",
            location="教二-202",
            note="",
            weekday=3,
            week_expr="1-4周(单)",
            period_expr="5-6节",
            odd_even="odd",
        )
    ]
    periods = {
        5: PeriodTime(start=time(14, 0), end=time(14, 45)),
        6: PeriodTime(start=time(14, 55), end=time(15, 40)),
    }

    events = expand_rules_to_occurrences(
        rules,
        term_start=date(2026, 2, 23),
        term_end=date(2026, 3, 31),
        periods=periods,
        timezone="Asia/Shanghai",
    )

    assert len(events) == 2
    assert events[0].week_no == 1
    assert events[1].week_no == 3
