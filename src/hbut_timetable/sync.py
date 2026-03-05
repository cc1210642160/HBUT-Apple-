from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import requests

from .expand import expand_rules_to_occurrences
from .ics import build_ics
from .models import CalendarMeta, PeriodTime, TermConfig
from .parser import parse_timetable_payload

DEFAULT_URL = "https://hbut.jw.chaoxing.com/admin/pkgl/xskb/queryKbForXsd"
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; HBUTTimetableSync/1.0; +https://github.com/)"


class SyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class SyncResult:
    event_count: int
    rule_count: int
    output_path: Path


@dataclass(frozen=True)
class CookieCheckResult:
    rule_count: int


def run_sync(
    *,
    cookie: str,
    ics_token: str,
    repo_root: Path,
    timetable_url: str = DEFAULT_URL,
    timeout_sec: int = 20,
    jitter_sec_min: int = 10,
    jitter_sec_max: int = 60,
    retries: int = 1,
    user_agent: str = DEFAULT_USER_AGENT,
    xnxq_override: str | None = None,
    apply_jitter: bool = True,
) -> SyncResult:
    if not cookie.strip():
        raise SyncError("HBUT_COOKIE is empty.")
    if not ics_token.strip():
        raise SyncError("ICS_TOKEN is empty.")

    term_cfg = _load_term_config(repo_root / "config" / "term.json", xnxq_override=xnxq_override)
    calendar_meta = _load_calendar_meta(repo_root / "config" / "calendar_meta.json")
    periods = _load_periods(repo_root / "config" / "periods.json")

    if apply_jitter and jitter_sec_max > 0:
        time.sleep(random.randint(jitter_sec_min, jitter_sec_max))

    payload, content_type = _fetch_timetable_payload(
        cookie=cookie,
        timetable_url=timetable_url,
        xnxq=term_cfg.xnxq,
        timeout_sec=timeout_sec,
        retries=retries,
        user_agent=user_agent,
    )

    rules = parse_timetable_payload(payload, content_type=content_type)
    if not rules:
        raise SyncError(
            "No course rules parsed. Provide a real payload fixture and update parser if site schema changed."
        )

    events = expand_rules_to_occurrences(
        rules,
        term_start=term_cfg.term_start,
        term_end=term_cfg.term_end,
        periods=periods,
        timezone=calendar_meta.timezone,
    )

    ics_text = build_ics(
        events,
        calendar_name=calendar_meta.name,
        prodid=calendar_meta.prodid,
        timezone=calendar_meta.timezone,
    )

    docs_dir = repo_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    output_path = docs_dir / f"{ics_token}.ics"
    output_path.write_text(ics_text, encoding="utf-8")

    meta_path = docs_dir / "latest-sync.json"
    meta = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "event_count": len(events),
        "rule_count": len(rules),
        "xnxq": term_cfg.xnxq,
        "output": output_path.name,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return SyncResult(event_count=len(events), rule_count=len(rules), output_path=output_path)


def validate_cookie_only(
    *,
    cookie: str,
    repo_root: Path,
    timetable_url: str = DEFAULT_URL,
    timeout_sec: int = 20,
    retries: int = 1,
    user_agent: str = DEFAULT_USER_AGENT,
    xnxq_override: str | None = None,
) -> CookieCheckResult:
    if not cookie.strip():
        raise SyncError("HBUT_COOKIE is empty.")

    term_cfg = _load_term_config(repo_root / "config" / "term.json", xnxq_override=xnxq_override)
    payload, content_type = _fetch_timetable_payload(
        cookie=cookie,
        timetable_url=timetable_url,
        xnxq=term_cfg.xnxq,
        timeout_sec=timeout_sec,
        retries=retries,
        user_agent=user_agent,
    )
    rules = parse_timetable_payload(payload, content_type=content_type)
    if not rules:
        raise SyncError("Cookie is valid but parser produced 0 rules; check payload schema.")
    return CookieCheckResult(rule_count=len(rules))


def _fetch_timetable_payload(
    *,
    cookie: str,
    timetable_url: str,
    xnxq: str,
    timeout_sec: int,
    retries: int,
    user_agent: str,
) -> tuple[str, str]:
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent, "Cookie": cookie})

    params = {"xnxq": xnxq}
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            resp = session.get(timetable_url, params=params, timeout=timeout_sec, allow_redirects=True)
            final_url = resp.url.lower()
            body = resp.text
            content_type = resp.headers.get("content-type", "")

            if resp.status_code >= 400:
                raise SyncError(f"Timetable request failed: HTTP {resp.status_code}")

            if "login" in final_url or "统一身份认证" in body or "authserver" in final_url:
                raise SyncError("Cookie seems invalid/expired: redirected to login.")

            return body, content_type
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                # Single retry with mild backoff to reduce burst pressure.
                time.sleep(2 + attempt)
                continue
            break

    raise SyncError(f"Failed to fetch timetable payload: {last_error}")


def _load_term_config(path: Path, xnxq_override: str | None = None) -> TermConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    xnxq = xnxq_override or raw["xnxq"]
    return TermConfig(
        xnxq=xnxq,
        term_start=datetime.strptime(raw["term_start"], "%Y-%m-%d").date(),
        term_end=datetime.strptime(raw["term_end"], "%Y-%m-%d").date(),
        timezone=raw.get("timezone", "Asia/Shanghai"),
    )


def _load_calendar_meta(path: Path) -> CalendarMeta:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return CalendarMeta(
        name=raw["name"],
        prodid=raw.get("prodid", "-//HBUT Timetable//EN"),
        timezone=raw.get("timezone", "Asia/Shanghai"),
    )


def _load_periods(path: Path) -> dict[int, PeriodTime]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[int, PeriodTime] = {}
    for key, val in raw.items():
        idx = int(key)
        out[idx] = PeriodTime(
            start=datetime.strptime(val["start"], "%H:%M").time(),
            end=datetime.strptime(val["end"], "%H:%M").time(),
        )
    return out


def load_env_or_fail(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SyncError(f"Environment variable missing: {name}")
    return value
