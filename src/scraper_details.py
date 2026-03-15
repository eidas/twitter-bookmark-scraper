import asyncio
import re
import random

from tenacity import retry, stop_after_attempt, wait_exponential

from src.browser import connect_browser
from src.config import load_config
from src.sheets import get_pending_urls, get_sheets_client, get_worksheet, update_details


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
async def safe_goto(page, url: str) -> None:
    await page.goto(url, wait_until="networkidle", timeout=30000)


async def rate_limited_wait() -> None:
    await asyncio.sleep(random.uniform(3.0, 5.0))


async def extract_post_details(page, url: str) -> dict:
    await safe_goto(page, url)
    await asyncio.sleep(2)

    post_date = None
    time_el = await page.query_selector('article[data-testid="tweet"] time')
    if time_el:
        post_date = await time_el.get_attribute("datetime")

    images = []
    img_elements = await page.query_selector_all(
        'article[data-testid="tweet"] img[src*="pbs.twimg.com/media"]'
    )
    for img in img_elements:
        src = await img.get_attribute("src")
        if src:
            images.append(src)

    return {"post_date": post_date or "", "image_urls": images}


def to_small_image_url(original_url: str) -> str:
    base = re.split(r"[?.]", original_url)[0]
    ext_match = re.search(r"\.(jpg|jpeg|png|webp)", original_url)
    fmt = ext_match.group(1) if ext_match else "jpg"
    return f"{base}?format={fmt}&name=small"


def build_image_formula(image_urls: list[str]) -> str:
    if not image_urls:
        return ""
    small_url = to_small_image_url(image_urls[0])
    return f'=IMAGE("{small_url}")'


async def fetch_details(config: dict) -> None:
    client = get_sheets_client(config["credentials_path"])
    worksheet = get_worksheet(client, config["spreadsheet_id"], config["worksheet_name"])

    pending = get_pending_urls(worksheet)
    if not pending:
        print("処理対象のポストがありません。")
        return

    print(f"{len(pending)} 件のポストの詳細を取得します...")

    async with connect_browser(config["cdp_endpoint"]) as context:
        page = await context.new_page()

        for i, item in enumerate(pending, start=1):
            url = item["url"]
            row = item["row"]
            print(f"[{i}/{len(pending)}] {url}")

            try:
                details = await extract_post_details(page, url)
                formula = build_image_formula(details["image_urls"])
                update_details(worksheet, row, details["post_date"], formula)
                print(f"  → 投稿日時: {details['post_date']}, 画像: {len(details['image_urls'])} 枚")
            except Exception as e:
                print(f"  → エラー: {e}")

            await rate_limited_wait()

    print("詳細取得が完了しました。")
