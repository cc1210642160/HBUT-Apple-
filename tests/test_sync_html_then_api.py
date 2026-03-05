from pathlib import Path

from hbut_timetable.sync import run_sync

HTML_FIXTURE = Path("tests/fixtures/query_page_minimal.html").read_text(encoding="utf-8")
API_FIXTURE = Path("tests/fixtures/sdpkkbList_payload.json").read_text(encoding="utf-8")


class DummyResp:
    def __init__(self, url: str, text: str, content_type: str, status_code: int = 200):
        self.url = url
        self.text = text
        self.headers = {"content-type": content_type}
        self.status_code = status_code


class DummySession:
    def __init__(self):
        self.headers = {}

    def get(self, url, params=None, timeout=None, allow_redirects=True):
        if "queryKbForXsd" in url:
            return DummyResp(url=url, text=HTML_FIXTURE, content_type="text/html")
        if "sdpkkbList" in url:
            return DummyResp(url=url, text=API_FIXTURE, content_type="application/json")
        raise AssertionError(f"Unexpected URL: {url}")


def test_sync_falls_back_to_sdpkkb_list(monkeypatch, tmp_path: Path):
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
        '{"1":{"start":"08:00","end":"08:45"},"5":{"start":"14:00","end":"14:45"}}',
        encoding="utf-8",
    )

    monkeypatch.setattr(sync_mod.requests, "Session", DummySession)
    result = run_sync(cookie="foo=bar", ics_token="tok123", repo_root=tmp_path, apply_jitter=False)

    assert result.rule_count == 2
    assert result.event_count > 0
