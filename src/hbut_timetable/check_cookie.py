from __future__ import annotations

import argparse
from pathlib import Path

from .sync import SyncError, load_env_or_fail, validate_cookie_only


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate HBUT cookie against timetable endpoint")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--xnxq", default=None, help="Override term identifier")
    parser.add_argument("--timetable-url", default=None, help="Override timetable endpoint URL")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        result = validate_cookie_only(
            cookie=load_env_or_fail("HBUT_COOKIE"),
            repo_root=Path(args.repo_root).resolve(),
            xnxq_override=args.xnxq,
            timetable_url=args.timetable_url or "https://hbut.jw.chaoxing.com/admin/pkgl/xskb/queryKbForXsd",
        )
        print(f"Cookie valid. Parsed rules: {result.rule_count}")
        return 0
    except SyncError as exc:
        print(f"Cookie invalid or parsing failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
