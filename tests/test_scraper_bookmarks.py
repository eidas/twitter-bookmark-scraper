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
    page = AsyncMock()
    articles = [
        make_article("/user1/status/111", "2025-06-15T10:00:00Z"),
        make_article("/user2/status/222", "2025-06-14T10:00:00Z"),
    ]
    page.query_selector_all = AsyncMock(side_effect=[articles, articles])
    page.evaluate = AsyncMock()

    result = await extract_bookmark_urls(page, cutoff_date=None)

    assert len(result) == 2
    assert result[0]["url"] == "https://x.com/user1/status/111"
    assert result[1]["url"] == "https://x.com/user2/status/222"


@pytest.mark.asyncio
async def test_extract_does_not_stop_on_single_old_post():
    """cutoff より古い投稿が1件あっても、直後に新しい投稿があれば停止しない"""
    page = AsyncMock()
    articles = [
        make_article("/user1/status/111", "2025-06-15T10:00:00Z"),
        make_article("/user2/status/222", "2024-12-01T10:00:00Z"),  # Before cutoff
        make_article("/user3/status/333", "2025-03-01T10:00:00Z"),  # After cutoff
    ]
    page.query_selector_all = AsyncMock(side_effect=[articles, articles])
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
    # 閾値分の古い投稿を追加
    for i in range(CUTOFF_CONSECUTIVE_THRESHOLD):
        articles.append(make_article(f"/old/status/{200 + i}", "2024-06-01T10:00:00Z"))
    # 停止後に到達しないはずの投稿
    articles.append(make_article("/new/status/999", "2025-08-01T10:00:00Z"))

    page.query_selector_all = AsyncMock(return_value=articles)
    page.evaluate = AsyncMock()

    cutoff = datetime(2025, 1, 1)
    result = await extract_bookmark_urls(page, cutoff_date=cutoff)

    # 最初の1件 + 古い投稿(閾値-1)件（閾値に達した時点で return するので最後の1件は含まない）
    assert result[0]["url"] == "https://x.com/user1/status/111"
    # 閾値到達時に停止するので、最後の新しい投稿は含まれない
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
    page.query_selector_all = AsyncMock(side_effect=[articles, articles])
    page.evaluate = AsyncMock()

    cutoff = datetime(2025, 1, 1)
    result = await extract_bookmark_urls(page, cutoff_date=cutoff)

    # 連続が途切れるため全件収集される
    assert len(result) == 5


@pytest.mark.asyncio
async def test_extract_deduplicates():
    page = AsyncMock()
    articles = [
        make_article("/user1/status/111", "2025-06-15T10:00:00Z"),
        make_article("/user1/status/111", "2025-06-15T10:00:00Z"),  # Duplicate
    ]
    page.query_selector_all = AsyncMock(side_effect=[articles, articles])
    page.evaluate = AsyncMock()

    result = await extract_bookmark_urls(page, cutoff_date=None)

    assert len(result) == 1
