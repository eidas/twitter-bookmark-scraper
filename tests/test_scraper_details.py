import pytest

from src.scraper_details import to_small_image_url, build_image_formula


class TestToSmallImageUrl:
    def test_jpg(self):
        url = "https://pbs.twimg.com/media/AbCdEf.jpg"
        result = to_small_image_url(url)
        assert result == "https://pbs.twimg.com/media/AbCdEf?format=jpg&name=small"

    def test_png(self):
        url = "https://pbs.twimg.com/media/AbCdEf.png"
        result = to_small_image_url(url)
        assert result == "https://pbs.twimg.com/media/AbCdEf?format=png&name=small"

    def test_webp(self):
        url = "https://pbs.twimg.com/media/AbCdEf.webp"
        result = to_small_image_url(url)
        assert result == "https://pbs.twimg.com/media/AbCdEf?format=webp&name=small"

    def test_url_with_existing_params(self):
        url = "https://pbs.twimg.com/media/AbCdEf?format=jpg&name=large"
        result = to_small_image_url(url)
        assert result == "https://pbs.twimg.com/media/AbCdEf?format=jpg&name=small"

    def test_no_extension_defaults_to_jpg(self):
        url = "https://pbs.twimg.com/media/AbCdEf"
        result = to_small_image_url(url)
        assert result == "https://pbs.twimg.com/media/AbCdEf?format=jpg&name=small"


class TestBuildImageFormula:
    def test_single_image(self):
        urls = ["https://pbs.twimg.com/media/AbCdEf.jpg"]
        result = build_image_formula(urls)
        assert result == '=IMAGE("https://pbs.twimg.com/media/AbCdEf?format=jpg&name=small")'

    def test_multiple_images_uses_first(self):
        urls = [
            "https://pbs.twimg.com/media/First.jpg",
            "https://pbs.twimg.com/media/Second.png",
        ]
        result = build_image_formula(urls)
        assert "First" in result
        assert "Second" not in result

    def test_empty_list(self):
        result = build_image_formula([])
        assert result == ""
