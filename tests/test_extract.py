from unittest.mock import MagicMock, patch

import pytest
import requests

from app.extract import RETRYABLE_STATUS_CODES, create_http_session, fetch_page
from app.errors import ETLExtractError


def test_create_http_session_configures_retry():
    session = create_http_session(max_retries=3, backoff_factor=1.5)
    adapter = session.get_adapter("https://")

    assert adapter.max_retries.total == 3
    assert adapter.max_retries.backoff_factor == 1.5
    assert adapter.max_retries.status_forcelist == RETRYABLE_STATUS_CODES


def test_create_http_session_no_retry_when_zero():
    session = create_http_session(max_retries=0, backoff_factor=1.0)
    adapter = session.get_adapter("https://")
    assert adapter.max_retries.total == 0


@patch("app.extract.create_http_session")
def test_fetch_page_returns_rows(mock_create_session):
    mock_response = MagicMock()
    mock_response.json.return_value = {"value": [{"SpatialDim": "USA"}]}
    mock_response.raise_for_status = MagicMock()

    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_create_session.return_value = mock_session

    rows = fetch_page(skip=0, top=10, max_retries=2)

    assert rows == [{"SpatialDim": "USA"}]
    mock_session.get.assert_called_once()
    mock_session.close.assert_called_once()


@patch("app.extract.create_http_session")
def test_fetch_page_raises_after_retries_exhausted(mock_create_session):
    mock_session = MagicMock()
    mock_session.get.side_effect = requests.ConnectionError("connection reset")
    mock_create_session.return_value = mock_session

    with pytest.raises(ETLExtractError, match="failed after"):
        fetch_page(skip=0, top=10, max_retries=3)

    mock_session.close.assert_called_once()
