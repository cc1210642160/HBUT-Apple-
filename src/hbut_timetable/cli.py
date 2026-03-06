from __future__ import annotations

import argparse
from pathlib import Path

from .sync import SyncError, load_env_or_fail, run_sync


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync HBUT timetable to ICS")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--xnxq", default=None, help="Override term identifier, e.g. 2025-2026-2")
    parser.add_argument("--no-jitter", action="store_true", help="Disable random anti-ban jitter")
    parser.add_argument("--timetable-url", default=None, help="Override timetable endpoint URL")
    parser.add_argument("--skip-meta", action="store_true", help="Do not write latest-sync.json")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        result = run_sync(
            cookie=load_env_or_fail("HBUT_COOKIE"),
            ics_token=load_env_or_fail("ICS_TOKEN"),
            repo_root=Path(args.repo_root).resolve(),
            xnxq_override=args.xnxq,
            timetable_url=args.timetable_url or "https://hbut.jw.chaoxing.com/admin/pkgl/xskb/queryKbForXsd",
            apply_jitter=not args.no_jitter,
            write_meta=not args.skip_meta,
        )
        print(f"Sync completed: rules={result.rule_count}, events={result.event_count}")
        return 0
    except SyncError as exc:
        print(f"Sync failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
