from pathlib import Path

from hbut_timetable.parser import parse_timetable_payload


def test_parse_json_payload_extracts_rules():
    payload = Path("tests/fixtures/sample_payload.json").read_text(encoding="utf-8")
    rules = parse_timetable_payload(payload, content_type="application/json")

    assert len(rules) == 2
    assert rules[0].course_name == "高等数学"
    assert rules[0].weekday == 1
    assert rules[0].week_expr == "1-16周"
    assert rules[0].period_expr == "1-2节"
    assert rules[1].odd_even == "odd"
