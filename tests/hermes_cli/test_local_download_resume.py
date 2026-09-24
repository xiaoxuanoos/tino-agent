"""A broken CDN range must resume without corrupting the staged GGUF."""

from __future__ import annotations

import io
import threading

from hermes_cli.web_routers import local_models


class _RangeResponse(io.BytesIO):
    status = 206

    def __init__(self, data: bytes, start: int, end: int):
        super().__init__(data)
        self.headers = {"Content-Range": f"bytes {start}-{end}/16"}


def test_range_download_resumes_only_missing_suffix(tmp_path, monkeypatch):
    original = b"0123456789abcdef"
    calls: list[tuple[int, int]] = []
    lock = threading.Lock()

    def urlopen(request, timeout=120):
        header = request.headers["Range"].removeprefix("bytes=")
        start, end = map(int, header.split("-"))
        with lock:
            calls.append((start, end))
            first_chunk = (start, end) == (0, 1) and calls.count((0, 1)) == 1
        return _RangeResponse(original[start:start + 1] if first_chunk else original[start:end + 1], start, end)

    monkeypatch.setattr(local_models, "_probe_range_support", lambda _url: len(original))
    monkeypatch.setattr(local_models.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(local_models.time, "sleep", lambda _: None)
    dest = tmp_path / "model.gguf"
    job = {"done_bytes": 0, "total_bytes": len(original)}

    local_models.download_file("https://example.test/model.gguf", dest, job)

    assert dest.read_bytes() == original
    assert (1, 1) in calls
    assert job["done_bytes"] == len(original)
    assert not dest.with_suffix(".part").exists()
