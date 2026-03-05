from pathlib import Path

from hbut_timetable.sync import run_sync

FIXTURE = Path("tests/fixtures/sample_payload.json").read_text(encoding="utf-8")


class DummyResp:
    status_code = 200
    url = "https://hbut.jw.chaoxing.com/admin/pkgl/xskb/queryKbForXsd?xnxq=2025-2026-2"
    text = FIXTURE
    headers = {"content-type": "application/json"}


class DummySession:
    def __init__(self):
        self.headers = {}

    def get(self, *args, **kwargs):
        return DummyResp()


def test_run_sync_writes_ics_and_meta(monkeypatch, tmp_path: Path):
    import hbut_timetable.sync as sync_mod

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
        '{"1":{"start":"08:00","end":"08:45"},"2":{"start":"08:55","end":"09:40"},"5":{"start":"14:00","end":"14:45"},"6":{"start":"14:55","end":"15:40"}}',
        encoding="utf-8",
    )

    monkeypatch.setattr(sync_mod.requests, "Session", DummySession)

    result = run_sync(cookie="foo=bar", ics_token="tok123", repo_root=tmp_path, apply_jitter=False)

    assert result.rule_count == 2
    assert result.event_count > 0
    assert (tmp_path / "docs" / "tok123.ics").exists()
    assert (tmp_path / "docs" / "latest-sync.json").exists()
