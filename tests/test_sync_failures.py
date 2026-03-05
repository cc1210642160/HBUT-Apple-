from pathlib import Path

import pytest

from hbut_timetable.sync import SyncError, run_sync


class DummyResp:
    status_code = 200
    url = "https://hbut.jw.chaoxing.com/admin/login"
    text = "统一身份认证平台"
    headers = {"content-type": "text/html"}


class DummySession:
    def __init__(self):
        self.headers = {}

    def get(self, *args, **kwargs):
        return DummyResp()


@pytest.fixture
def repo_copy(tmp_path: Path):
    (tmp_path / "config").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "config" / "term.json").write_text(
        '{"xnxq":"2025-2026-2","term_start":"2026-02-23","term_end":"2026-07-05","timezone":"Asia/Shanghai"}',
        encoding="utf-8",
    )
    (tmp_path / "config" / "calendar_meta.json").write_text(
        '{"name":"HBUT 课程表","prodid":"-//HBUT//EN","timezone":"Asia/Shanghai"}', encoding="utf-8"
    )
    (tmp_path / "config" / "periods.json").write_text(
        '{"1":{"start":"08:00","end":"08:45"},"2":{"start":"08:55","end":"09:40"}}',
        encoding="utf-8",
    )
    return tmp_path


def test_sync_raises_when_cookie_expired(monkeypatch, repo_copy: Path):
    import hbut_timetable.sync as sync_mod

    monkeypatch.setattr(sync_mod.requests, "Session", DummySession)

    with pytest.raises(SyncError, match="Cookie seems invalid/expired"):
        run_sync(
            cookie="foo=bar",
            ics_token="token123",
            repo_root=repo_copy,
            apply_jitter=False,
        )
