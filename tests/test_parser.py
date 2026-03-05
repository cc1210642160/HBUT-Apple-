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


def test_parse_sdpkkb_list_payload_extracts_rules():
    payload = Path("tests/fixtures/sdpkkbList_payload.json").read_text(encoding="utf-8")
    rules = parse_timetable_payload(payload, content_type="application/json")

    assert len(rules) == 2
    assert rules[0].course_name == "高等数学"
    assert rules[0].teacher == "张老师"
    assert rules[0].location == "教一-101"
    assert rules[0].period_expr == "1节"
    assert rules[0].week_expr == "1-16周"


def test_parse_strips_html_tags_from_course_fields():
    payload = """
    {
      "ret": 0,
      "data": [{
        "kcmc": "<a href=\\"javascript:void(0)\\">数字电路</a>",
        "tmc": "<span>王老师</span>",
        "croommc": "<div>教三-301</div>",
        "xingqi": 2,
        "djc": 3,
        "zcstr": "1-16"
      }]
    }
    """
    rules = parse_timetable_payload(payload, content_type="application/json")
    assert len(rules) == 1
    assert rules[0].course_name == "数字电路"
    assert rules[0].teacher == "王老师"
    assert rules[0].location == "教三-301"
