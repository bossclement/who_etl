import pytest

from app.cli import parse_config
from app.config import DEFAULT_PAGE_SIZE, DEFAULT_WHO_API_BASE_URL


def test_parse_config_defaults():
    config = parse_config([])
    assert config.api_base_url == DEFAULT_WHO_API_BASE_URL
    assert config.page_size == DEFAULT_PAGE_SIZE
    assert config.skip is None
    assert config.reset is False
    assert config.max_batches is None


def test_parse_config_overrides():
    config = parse_config(
        ["--page-size", "50", "--skip", "200", "--max-batches", "3", "--timeout", "60"]
    )
    assert config.page_size == 50
    assert config.skip == 200
    assert config.max_batches == 3
    assert config.request_timeout_seconds == 60


def test_parse_config_rejects_reset_and_skip():
    with pytest.raises(SystemExit):
        parse_config(["--reset", "--skip", "0"])
