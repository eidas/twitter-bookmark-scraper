import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.scraper_bookmarks import extract_bookmark_urls


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
    # First call returns articles, second call returns same count (no new articles)
    page.query_selector_all = AsyncMock(side_effect=[articles, articles])
    page.evaluate = AsyncMock()

    result = await extract_bookmark_urls(page, cutoff_date=None)

    assert len(result) == 2
    assert result[0]["url"] == "https://x.com/user1/status/111"
    assert result[1]["url"] == "https://x.com/user2/status/222"


@pytest.mark.asyncio
async def test_extract_stops_at_cutoff():
    page = AsyncMock()
    articles = [
        make_article("/user1/status/111", "2025-06-15T10:00:00Z"),
        make_article("/user2/status/222", "2024-12-01T10:00:00Z"),  # Before cutoff
    ]
    page.query_selector_all = AsyncMock(return_value=articles)
    page.evaluate = AsyncMock()

    cutoff = datetime(2025, 1, 1)
    result = await extract_bookmark_urls(page, cutoff_date=cutoff)

    assert len(result) == 1
    assert result[0]["url"] == "https://x.com/user1/status/111"


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
