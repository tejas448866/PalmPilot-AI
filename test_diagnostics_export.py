"""Sanitized diagnostics export tests."""

import json
from pathlib import Path

from src import __version__
from src.diagnostics import export_diagnostics, sanitize


def test_sanitize_redacts_nested_credentials() -> None:
    assert sanitize({"password": "secret", "nested": {"api_key": "abc"}}) == {
        "password": "<redacted>",
        "nested": {"api_key": "<redacted>"},
    }


def test_diagnostics_export_is_bounded_and_versioned(tmp_path: Path) -> None:
    log = tmp_path / "controller.log"
    log.write_text("\n".join(f"line {index}" for index in range(10)), encoding="utf-8")
    output = export_diagnostics(
        tmp_path / "diagnostics.json",
        {"index": 0, "password": "do-not-export"},
        "generic_wasd",
        log,
        maximum_log_lines=3,
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["application"]["version"] == __version__
    assert report["camera"]["password"] == "<redacted>"
    assert report["recent_logs"] == ["line 7", "line 8", "line 9"]
