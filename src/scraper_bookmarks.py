import asyncio
import random
from datetime import datetime

from src.browser import connect_browser
from src.config import load_config
from src.sheets import append_bookmarks, get_existing_urls, get_sheets_client, get_worksheet


CUTOFF_CONSECUTIVE_THRESHOLD = 5


async def extract_bookmark_urls(page, cutoff_date: datetime | None) -> list[dict]:
    collected = []
    seen_urls = set()
    previous_count = 0
    consecutive_old = 0

    while True:
        articles = await page.query_selector_all('article[data-testid="tweet"]')

        for article in articles[previous_count:]:
            link = await article.query_selector('a[href*="/status/"]')
            if not link:
                continue
            href = await link.get_attribute("href")
            if not href:
                continue
            url = f"https://x.com{href}" if href.startswith("/") else href

            if url in seen_urls:
                continue
            seen_urls.add(url)

            datetime_str = ""
            time_el = await article.query_selector("time")
            if time_el:
                datetime_str = await time_el.get_attribute("datetime") or ""
                if cutoff_date and datetime_str:
                    post_dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                    if post_dt.replace(tzinfo=None) < cutoff_date:
                        consecutive_old += 1
                        if consecutive_old >= CUTOFF_CONSECUTIVE_THRESHOLD:
                            print(
                                f"cutoff_date ({cutoff_date}) より古い投稿が"
                                f" {CUTOFF_CONSECUTIVE_THRESHOLD} 件連続。収集を終了します。"
                            )
                            return collected
                        collected.append({"url": url, "datetime_hint": datetime_str})
                        continue
                    else:
                        consecutive_old = 0

            collected.append({"url": url, "datetime_hint": datetime_str})

        previous_count = len(articles)

        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(random.uniform(2.0, 3.0))

        new_articles = await page.query_selector_all('article[data-testid="tweet"]')
        if len(new_articles) == previous_count:
            break

    return collected


async def collect_bookmarks(config: dict) -> None:
    client = get_sheets_client(config["credentials_path"])
    worksheet = get_worksheet(client, config["spreadsheet_id"], config["worksheet_name"])

    cutoff_date = None
    if config.get("bookmark_cutoff_date"):
        cutoff_date = datetime.fromisoformat(config["bookmark_cutoff_date"])

    async with connect_browser(config["cdp_endpoint"]) as context:
        page = await context.new_page()
        await page.goto("https://x.com/i/bookmarks", wait_until="domcontentloaded")
        await page.wait_for_selector('article[data-testid="tweet"]', timeout=30000)

        print("ブックマークの収集を開始します...")
        bookmarks = await extract_bookmark_urls(page, cutoff_date)
        print(f"収集完了: {len(bookmarks)} 件のブックマークを検出")

        added = append_bookmarks(worksheet, bookmarks)
        print(f"Spreadsheet に {added} 件を追加しました（重複スキップ: {len(bookmarks) - added} 件）")
