import pytest

from src.browser import resolve_cdp_endpoint


def test_resolve_passes_through_http_endpoint():
    assert resolve_cdp_endpoint("http://localhost:9222") == "http://localhost:9222"


def test_resolve_chrome_reads_devtools_active_port(tmp_path):
    (tmp_path / "DevToolsActivePort").write_text(
        "9222\n/devtools/browser/abc-123\n", encoding="utf-8"
    )
    assert (
        resolve_cdp_endpoint("chrome", user_data_dir=tmp_path)
        == "ws://127.0.0.1:9222/devtools/browser/abc-123"
    )


def test_resolve_chrome_without_port_file(tmp_path):
    with pytest.raises(ConnectionError, match="chrome://inspect"):
        resolve_cdp_endpoint("chrome", user_data_dir=tmp_path)


def test_resolve_chrome_invalid_port_file(tmp_path):
    (tmp_path / "DevToolsActivePort").write_text("invalid", encoding="utf-8")
    with pytest.raises(ConnectionError, match="形式が不正"):
        resolve_cdp_endpoint("chrome", user_data_dir=tmp_path)
