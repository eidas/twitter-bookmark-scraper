import contextlib
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

# cdp_endpoint にこの値を指定すると、普段使いの Chrome に接続する
# (chrome://inspect/#remote-debugging でリモートデバッグを有効化しておく)
CHROME_ENDPOINT = "chrome"

# chrome://inspect でユーザーの許可ダイアログを待つため長めに取る
CONNECT_TIMEOUT_MS = 60_000

SETUP_INSTRUCTIONS = (
    "Chrome で chrome://inspect/#remote-debugging を開き、\n"
    "リモートデバッグを有効化してから再実行してください。\n"
    "接続時に Chrome に表示される確認ダイアログでは「許可」を選択してください。"
)


def default_chrome_user_data_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ["LOCALAPPDATA"]) / "Google" / "Chrome" / "User Data"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    return Path.home() / ".config" / "google-chrome"


def resolve_cdp_endpoint(cdp_endpoint: str, user_data_dir: Path | None = None) -> str:
    """cdp_endpoint を Playwright の connect_over_cdp に渡せる URL に解決する。

    "chrome" の場合は Chrome が書き出す DevToolsActivePort ファイルから
    WebSocket の URL を組み立てる。それ以外 (http:// / ws://) はそのまま返す。
    """
    if cdp_endpoint != CHROME_ENDPOINT:
        return cdp_endpoint

    port_file = (user_data_dir or default_chrome_user_data_dir()) / "DevToolsActivePort"
    if not port_file.exists():
        raise ConnectionError(
            f"Chrome のリモートデバッグが有効になっていません ({port_file} がありません)。\n"
            + SETUP_INSTRUCTIONS
        )

    lines = port_file.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2 or not lines[0].strip().isdigit():
        raise ConnectionError(f"DevToolsActivePort の形式が不正です: {port_file}")

    port, path = lines[0].strip(), lines[1].strip()
    return f"ws://127.0.0.1:{port}{path}"


@contextlib.asynccontextmanager
async def connect_browser(cdp_endpoint: str = CHROME_ENDPOINT):
    endpoint = resolve_cdp_endpoint(cdp_endpoint)

    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.connect_over_cdp(
            endpoint, timeout=CONNECT_TIMEOUT_MS
        )
    except Exception as e:
        await pw.stop()
        raise ConnectionError(
            f"Chrome に接続できません ({endpoint})。\n" + SETUP_INSTRUCTIONS
        ) from e

    context = browser.contexts[0]
    try:
        yield context
    finally:
        await pw.stop()
