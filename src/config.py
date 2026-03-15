import yaml
from pathlib import Path

REQUIRED_KEYS = ["spreadsheet_id", "worksheet_name", "credentials_path"]

DEFAULTS = {
    "cdp_endpoint": "http://localhost:9222",
}


def load_config(path: str = "./config.yaml") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError(f"設定ファイルの形式が不正です: {config_path}")

    for key in REQUIRED_KEYS:
        if key not in config or not config[key]:
            raise ValueError(f"必須設定項目が未設定です: {key}")

    for key, default in DEFAULTS.items():
        config.setdefault(key, default)

    return config
