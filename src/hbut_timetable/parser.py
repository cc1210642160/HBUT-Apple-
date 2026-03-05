from __future__ import annotations

import json
import re
from html import unescape
from typing import Any

from bs4 import BeautifulSoup

from .models import CourseRule

# Common key aliases seen in Chinese timetable systems.
KEY_ALIASES = {
    "course_name": ["kcmc", "courseName", "课程名称", "课程", "name"],
    "teacher": ["tmc", "jsxm", "teacherName", "教师", "任课教师", "teacher"],
    "location": ["croommc", "cdmc", "jsmc", "roomName", "上课地点", "地点", "location"],
    "note": ["remarks", "bz", "remark", "备注", "note"],
    "weekday": ["xingqi", "xqj", "weekday", "星期", "周几", "dayOfWeek"],
    "week_expr": ["zcstr", "zcd", "weekExpr", "周次", "weeks"],
    "period_expr": ["djc", "jcor", "jc", "section", "节次", "periods"],
    "odd_even": ["dsz", "oddEven", "单双周"],
}


def parse_timetable_payload(payload: str, content_type: str = "") -> list[CourseRule]:
    text = payload.strip()
    rules: list[CourseRule] = []

    # Try JSON first unless content type strongly indicates html.
    if "html" not in content_type.lower():
        rules = _parse_from_json_maybe(text)
        if rules:
            return rules

    if text.startswith("{") or text.startswith("["):
        rules = _parse_from_json_maybe(text)
        if rules:
            return rules

    rules = _parse_from_html(text)
    return _dedupe_rules(rules)


def _parse_from_json_maybe(text: str) -> list[CourseRule]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []

    items = _extract_record_dicts(data)
    rules: list[CourseRule] = []
    for item in items:
        rule = _rule_from_dict(item)
        if rule is not None:
            rules.append(rule)
    return _dedupe_rules(rules)


def _extract_record_dicts(data: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            keys = {str(k) for k in node.keys()}
            if _looks_like_course_record(keys):
                out.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return out


def _looks_like_course_record(keys: set[str]) -> bool:
    has_weekday = _has_alias(keys, "weekday")
    has_week = _has_alias(keys, "week_expr")
    has_period = _has_alias(keys, "period_expr")
    has_course = _has_alias(keys, "course_name")
    return has_weekday and has_week and has_period and has_course


def _has_alias(keys: set[str], logical_name: str) -> bool:
    for key in KEY_ALIASES[logical_name]:
        if key in keys:
            return True
    return False


def _get_str(item: dict[str, Any], logical_name: str) -> str:
    for key in KEY_ALIASES[logical_name]:
        if key in item and item[key] is not None:
            return _clean_text(str(item[key]))
    return ""


def _clean_text(value: str) -> str:
    # sdpkkbList fields may embed HTML snippets like <a href=...>课程名</a>.
    plain = BeautifulSoup(unescape(value), "html.parser").get_text(" ", strip=True)
    return plain.strip()


def _rule_from_dict(item: dict[str, Any]) -> CourseRule | None:
    course_name = _get_str(item, "course_name")
    week_expr = _normalize_week_expr(_get_str(item, "week_expr"))
    period_expr = _normalize_period_expr(_get_str(item, "period_expr"))
    weekday = _normalize_weekday(_get_str(item, "weekday"))

    if not course_name or not week_expr or not period_expr or weekday < 1 or weekday > 7:
        return None

    odd_even = _normalize_odd_even(_get_str(item, "odd_even"), week_expr)
    teacher = _get_str(item, "teacher")
    location = _get_str(item, "location")
    note = _get_str(item, "note")

    return CourseRule(
        course_name=course_name,
        teacher=teacher,
        location=location,
        note=note,
        weekday=weekday,
        week_expr=week_expr,
        period_expr=period_expr,
        odd_even=odd_even,
    )


def _parse_from_html(html: str) -> list[CourseRule]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    # Conservative fallback: parse lines that include week/day/section patterns.
    # Prefer a later JSON parser once real payload is provided.
    rules: list[CourseRule] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    for i, line in enumerate(lines):
        if "周" not in line or "节" not in line:
            continue
        week_expr_match = re.search(r"\d+\s*-\s*\d+\s*周(?:\((?:单|双)\))?|\d+(?:,\d+)*\s*周", line)
        period_expr_match = re.search(r"\d+\s*-\s*\d+\s*节|\d+(?:,\d+)*\s*节", line)
        weekday_match = re.search(r"周([一二三四五六日天])", line)
        if not (week_expr_match and period_expr_match and weekday_match):
            continue

        name = lines[i - 1] if i > 0 else "未命名课程"
        weekday = _cn_weekday_to_int(weekday_match.group(1))
        if weekday == 0:
            continue

        rules.append(
            CourseRule(
                course_name=name,
                teacher="",
                location="",
                note="parsed-from-html-fallback",
                weekday=weekday,
                week_expr=_normalize_week_expr(week_expr_match.group(0)),
                period_expr=_normalize_period_expr(period_expr_match.group(0)),
                odd_even=_normalize_odd_even("", week_expr_match.group(0)),
            )
        )

    return _dedupe_rules(rules)


def _normalize_weekday(value: str) -> int:
    value = value.strip()
    if not value:
        return 0
    if value.isdigit():
        day = int(value)
        if 1 <= day <= 7:
            return day
        # Some systems use 0=Sun.
        if day == 0:
            return 7
    if value.startswith("周") and len(value) >= 2:
        return _cn_weekday_to_int(value[-1])
    return _cn_weekday_to_int(value)


def _cn_weekday_to_int(ch: str) -> int:
    mapping = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "天": 7}
    return mapping.get(ch, 0)


def _normalize_week_expr(value: str) -> str:
    value = value.replace(" ", "")
    value = value.replace("第", "")
    value = value.replace("星期", "")
    if value and "周" not in value:
        value = value + "周"
    return value


def _normalize_period_expr(value: str) -> str:
    value = value.replace(" ", "")
    if value and "节" not in value and value.isdigit():
        value = value + "节"
    return value


def _normalize_odd_even(value: str, week_expr: str) -> str:
    v = value.strip()
    if "单" in v or "单" in week_expr:
        return "odd"
    if "双" in v or "双" in week_expr:
        return "even"
    return "all"


def _dedupe_rules(rules: list[CourseRule]) -> list[CourseRule]:
    seen: set[tuple[str, int, str, str, str, str]] = set()
    out: list[CourseRule] = []
    for r in rules:
        key = (r.course_name, r.weekday, r.week_expr, r.period_expr, r.location, r.teacher)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out
