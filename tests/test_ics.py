from datetime import datetime
from zoneinfo import ZoneInfo

from hbut_timetable.expand import EventOccurrence
from hbut_timetable.ics import build_ics


def test_ics_contains_required_fields_and_stable_uid():
    tz = ZoneInfo("Asia/Shanghai")
    event = EventOccurrence(
        course_name="高等数学",
        teacher="张老师",
        location="教一-101",
        note="",
        start_at=datetime(2026, 2, 23, 8, 0, tzinfo=tz),
        end_at=datetime(2026, 2, 23, 9, 40, tzinfo=tz),
        week_no=1,
        weekday=1,
        period_expr="1-2节",
    )

    ics_1 = build_ics([event], calendar_name="HBUT 课程表", prodid="-//TEST//EN")
    ics_2 = build_ics([event], calendar_name="HBUT 课程表", prodid="-//TEST//EN")

    assert "BEGIN:VCALENDAR" in ics_1
    assert "BEGIN:VEVENT" in ics_1
    assert "UID:" in ics_1
    assert "DTSTART;TZID=Asia/Shanghai:20260223T080000" in ics_1
    assert "DESCRIPTION:Teacher: 张老师" in ics_1
    assert "Week:" not in ics_1

    uid_1 = [ln for ln in ics_1.splitlines() if ln.startswith("UID:")][0]
    uid_2 = [ln for ln in ics_2.splitlines() if ln.startswith("UID:")][0]
    assert uid_1 == uid_2
