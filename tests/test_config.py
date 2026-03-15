import pytest
import yaml
from pathlib import Path

from src.config import load_config


@pytest.fixture
def valid_config(tmp_path):
    config_data = {
        "spreadsheet_id": "test_spreadsheet_id",
        "worksheet_name": "bookmarks",
        "credentials_path": "./credentials.json",
        "bookmark_cutoff_date": "2025-01-01T00:00:00",
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")
    return config_file


def test_load_config_success(valid_config):
    config = load_config(str(valid_config))
    assert config["spreadsheet_id"] == "test_spreadsheet_id"
    assert config["worksheet_name"] == "bookmarks"
    assert config["credentials_path"] == "./credentials.json"


def test_load_config_sets_defaults(valid_config):
    config = load_config(str(valid_config))
    assert config["cdp_endpoint"] == "http://localhost:9222"


def test_load_config_preserves_custom_cdp(tmp_path):
    config_data = {
        "spreadsheet_id": "id",
        "worksheet_name": "sheet",
        "credentials_path": "./creds.json",
        "cdp_endpoint": "http://localhost:9333",
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    config = load_config(str(config_file))
    assert config["cdp_endpoint"] == "http://localhost:9333"


def test_load_config_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/config.yaml")


def test_load_config_missing_required_key(tmp_path):
    config_data = {
        "spreadsheet_id": "id",
        # worksheet_name is missing
        "credentials_path": "./creds.json",
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    with pytest.raises(ValueError, match="worksheet_name"):
        load_config(str(config_file))


def test_load_config_empty_required_key(tmp_path):
    config_data = {
        "spreadsheet_id": "",
        "worksheet_name": "bookmarks",
        "credentials_path": "./creds.json",
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    with pytest.raises(ValueError, match="spreadsheet_id"):
        load_config(str(config_file))


def test_load_config_invalid_format(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("just a string", encoding="utf-8")

    with pytest.raises(ValueError, match="形式が不正"):
        load_config(str(config_file))
