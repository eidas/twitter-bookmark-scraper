import contextlib
from playwright.async_api import async_playwright


@contextlib.asynccontextmanager
async def connect_browser(cdp_endpoint: str = "http://localhost:9222"):
    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.connect_over_cdp(cdp_endpoint)
    except Exception as e:
        await pw.stop()
        raise ConnectionError(
            f"Chrome に接続できません ({cdp_endpoint})。\n"
            "以下のコマンドでデバッグポート付きの Chrome を起動してください:\n"
            '  google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-debug-profile"'
        ) from e

    context = browser.contexts[0]
    try:
        yield context
    finally:
        await pw.stop()
