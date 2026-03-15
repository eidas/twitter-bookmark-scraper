import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.scraper_bookmarks import extract_bookmark_urls, CUTOFF_CONSECUTIVE_THRESHOLD


def make_article(href, datetime_str=None):
    """テスト用の article モックを作成する"""
    article = AsyncMock()
    link = AsyncMock()
    link.get_attribute = AsyncMock(return_value=href)
    article.query_selector = AsyncMock(side_effect=lambda sel: link if "status" in sel else _make_time(datetime_str))
    return article


def _make_time(datetime_str):
    if datetime_str is None:
        return None
    time_el = AsyncMock()
    time_el.get_attribute = AsyncMock(return_value=datetime_str)
    return time_el


@pytest.mark.asyncio
async def test_extract_collects_urls():
    """仮想スクロールを模擬: 1回目と2回目で異なる article が返る"""
    page = AsyncMock()
    batch1 = [
        make_article("/user1/status/111", "2025-06-15T10:00:00Z"),
        make_article("/user2/status/222", "2025-06-14T10:00:00Z"),
    ]
    batch2 = [
        make_article("/user3/status/333", "2025-06-13T10:00:00Z"),
    ]
    # batch1 → スクロール → batch2 → スクロール → batch2(同じ=新規なし) ×3回
    page.query_selector_all = AsyncMock(
        side_effect=[batch1, batch2, batch2, batch2, batch2]
    )
    page.evaluate = AsyncMock()

    result = await extract_bookmark_urls(page, cutoff_date=None)

    assert len(result) == 3
    assert result[0]["url"] == "https://x.com/user1/status/111"
    assert result[1]["url"] == "https://x.com/user2/status/222"
    assert result[2]["url"] == "https://x.com/user3/status/333"


@pytest.mark.asyncio
async def test_extract_does_not_stop_on_single_old_post():
    """cutoff より古い投稿が1件あっても、直後に新しい投稿があれば停止しない"""
    page = AsyncMock()
    articles = [
        make_article("/user1/status/111", "2025-06-15T10:00:00Z"),
        make_article("/user2/status/222", "2024-12-01T10:00:00Z"),  # Before cutoff
        make_article("/user3/status/333", "2025-03-01T10:00:00Z"),  # After cutoff
    ]
    # 1回目 → スクロール → 同じ記事(新規なし) ×3回
    page.query_selector_all = AsyncMock(
        side_effect=[articles, articles, articles, articles]
    )
    page.evaluate = AsyncMock()

    cutoff = datetime(2025, 1, 1)
    result = await extract_bookmark_urls(page, cutoff_date=cutoff)

    assert len(result) == 3
    assert result[0]["url"] == "https://x.com/user1/status/111"
    assert result[1]["url"] == "https://x.com/user2/status/222"
    assert result[2]["url"] == "https://x.com/user3/status/333"


@pytest.mark.asyncio
async def test_extract_stops_after_consecutive_old_posts():
    """cutoff より古い投稿が連続で閾値に達したら停止する"""
    page = AsyncMock()
    articles = [
        make_article("/user1/status/111", "2025-06-15T10:00:00Z"),
    ]
    for i in range(CUTOFF_CONSECUTIVE_THRESHOLD):
        articles.append(make_article(f"/old/status/{200 + i}", "2024-06-01T10:00:00Z"))
    articles.append(make_article("/new/status/999", "2025-08-01T10:00:00Z"))

    page.query_selector_all = AsyncMock(return_value=articles)
    page.evaluate = AsyncMock()

    cutoff = datetime(2025, 1, 1)
    result = await extract_bookmark_urls(page, cutoff_date=cutoff)

    assert result[0]["url"] == "https://x.com/user1/status/111"
    assert not any(r["url"] == "https://x.com/new/status/999" for r in result)


@pytest.mark.asyncio
async def test_extract_resets_consecutive_count():
    """cutoff より新しい投稿が間に入ると連続カウントがリセットされる"""
    page = AsyncMock()
    articles = [
        make_article("/old/status/1", "2024-06-01T10:00:00Z"),
        make_article("/old/status/2", "2024-07-01T10:00:00Z"),
        make_article("/new/status/3", "2025-06-01T10:00:00Z"),  # Reset
        make_article("/old/status/4", "2024-08-01T10:00:00Z"),
        make_article("/old/status/5", "2024-09-01T10:00:00Z"),
    ]
    # 1回目 → スクロール → 同じ記事(新規なし) ×3回
    page.query_selector_all = AsyncMock(
        side_effect=[articles, articles, articles, articles]
    )
    page.evaluate = AsyncMock()

    cutoff = datetime(2025, 1, 1)
    result = await extract_bookmark_urls(page, cutoff_date=cutoff)

    assert len(result) == 5


@pytest.mark.asyncio
async def test_extract_deduplicates():
    """仮想スクロールで同じ article が繰り返し現れても重複しない"""
    page = AsyncMock()
    articles = [
        make_article("/user1/status/111", "2025-06-15T10:00:00Z"),
        make_article("/user1/status/111", "2025-06-15T10:00:00Z"),  # Duplicate
    ]
    # 同じ記事しかないので新規なし×3回で終了
    page.query_selector_all = AsyncMock(
        side_effect=[articles, articles, articles, articles]
    )
    page.evaluate = AsyncMock()

    result = await extract_bookmark_urls(page, cutoff_date=None)

    assert len(result) == 1


@pytest.mark.asyncio
async def test_extract_virtual_scroll_replaces_articles():
    """仮想スクロール: DOM上のarticle数は一定だが中身が入れ替わる"""
    page = AsyncMock()
    # スクロールごとにDOMの中身が入れ替わる（件数は同じ2件）
    batch1 = [
        make_article("/user/status/1", "2025-06-15T10:00:00Z"),
        make_article("/user/status/2", "2025-06-14T10:00:00Z"),
    ]
    batch2 = [
        make_article("/user/status/2", "2025-06-14T10:00:00Z"),  # 重複
        make_article("/user/status/3", "2025-06-13T10:00:00Z"),  # 新規
    ]
    batch3 = [
        make_article("/user/status/3", "2025-06-13T10:00:00Z"),  # 重複
        make_article("/user/status/4", "2025-06-12T10:00:00Z"),  # 新規
    ]
    # batch3 が繰り返されて新規なし×3回で終了
    page.query_selector_all = AsyncMock(
        side_effect=[batch1, batch2, batch3, batch3, batch3, batch3]
    )
    page.evaluate = AsyncMock()

    result = await extract_bookmark_urls(page, cutoff_date=None)

    urls = [r["url"] for r in result]
    assert urls == [
        "https://x.com/user/status/1",
        "https://x.com/user/status/2",
        "https://x.com/user/status/3",
        "https://x.com/user/status/4",
    ]
