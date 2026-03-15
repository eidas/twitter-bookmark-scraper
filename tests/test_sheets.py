import pytest
from unittest.mock import MagicMock

from src.sheets import append_bookmarks, get_existing_urls, get_pending_urls, update_details


@pytest.fixture
def mock_worksheet():
    return MagicMock()


class TestGetExistingUrls:
    def test_returns_set_of_urls(self, mock_worksheet):
        mock_worksheet.col_values.return_value = [
            "https://x.com/user/status/1",
            "https://x.com/user/status/2",
        ]
        result = get_existing_urls(mock_worksheet)
        assert result == {
            "https://x.com/user/status/1",
            "https://x.com/user/status/2",
        }

    def test_returns_empty_set_when_no_data(self, mock_worksheet):
        mock_worksheet.col_values.return_value = []
        result = get_existing_urls(mock_worksheet)
        assert result == set()


class TestAppendBookmarks:
    def test_appends_new_bookmarks(self, mock_worksheet):
        mock_worksheet.col_values.return_value = []
        bookmarks = [
            {"url": "https://x.com/user/status/1", "datetime_hint": "2025-06-15T10:00:00"},
            {"url": "https://x.com/user/status/2", "datetime_hint": "2025-06-15T11:00:00"},
        ]
        count = append_bookmarks(mock_worksheet, bookmarks)
        assert count == 2
        mock_worksheet.append_rows.assert_called_once()

    def test_skips_duplicates(self, mock_worksheet):
        mock_worksheet.col_values.return_value = ["https://x.com/user/status/1"]
        bookmarks = [
            {"url": "https://x.com/user/status/1", "datetime_hint": "2025-06-15T10:00:00"},
            {"url": "https://x.com/user/status/2", "datetime_hint": "2025-06-15T11:00:00"},
        ]
        count = append_bookmarks(mock_worksheet, bookmarks)
        assert count == 1

    def test_no_append_when_all_duplicates(self, mock_worksheet):
        mock_worksheet.col_values.return_value = ["https://x.com/user/status/1"]
        bookmarks = [
            {"url": "https://x.com/user/status/1", "datetime_hint": "2025-06-15T10:00:00"},
        ]
        count = append_bookmarks(mock_worksheet, bookmarks)
        assert count == 0
        mock_worksheet.append_rows.assert_not_called()


class TestGetPendingUrls:
    def test_returns_pending_rows(self, mock_worksheet):
        mock_worksheet.get_all_values.return_value = [
            ["https://x.com/user/status/1", "2025-06-15", "pending", ""],
            ["https://x.com/user/status/2", "2025-06-15", "keep", ""],
            ["https://x.com/user/status/3", "2025-06-15", "remove", ""],
        ]
        result = get_pending_urls(mock_worksheet)
        assert len(result) == 2
        assert result[0] == {"row": 1, "url": "https://x.com/user/status/1"}
        assert result[1] == {"row": 2, "url": "https://x.com/user/status/2"}

    def test_skips_rows_with_details(self, mock_worksheet):
        mock_worksheet.get_all_values.return_value = [
            ["https://x.com/user/status/1", "2025-06-15", "keep", "2025-06-14"],
        ]
        result = get_pending_urls(mock_worksheet)
        assert len(result) == 0

    def test_skips_short_rows(self, mock_worksheet):
        mock_worksheet.get_all_values.return_value = [
            ["https://x.com/user/status/1", "2025-06-15"],
        ]
        result = get_pending_urls(mock_worksheet)
        assert len(result) == 0


class TestUpdateDetails:
    def test_updates_date_and_image(self, mock_worksheet):
        update_details(mock_worksheet, 5, "2025-06-14T08:00:00", '=IMAGE("url")')
        mock_worksheet.update_cell.assert_any_call(5, 4, "2025-06-14T08:00:00")
        mock_worksheet.update_cell.assert_any_call(5, 5, '=IMAGE("url")')

    def test_skips_image_when_empty(self, mock_worksheet):
        update_details(mock_worksheet, 5, "2025-06-14T08:00:00", "")
        mock_worksheet.update_cell.assert_called_once_with(5, 4, "2025-06-14T08:00:00")
