import requests

from app.config import DEFAULT_PAGE_SIZE, DEFAULT_REQUEST_TIMEOUT_SECONDS, DEFAULT_WHO_API_BASE_URL
from app.errors import ETLExtractError
from app.logger import get_logger

logger = get_logger(__name__)


def fetch_page(
    skip: int = 0,
    top: int = DEFAULT_PAGE_SIZE,
    *,
    api_base_url: str = DEFAULT_WHO_API_BASE_URL,
    request_timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> list:
    url = f"{api_base_url}?$top={top}&$skip={skip}"

    logger.info("Fetching data: skip=%s, top=%s", skip, top)

    try:
        response = requests.get(url, timeout=request_timeout_seconds)
        response.raise_for_status()
    except requests.Timeout as e:
        raise ETLExtractError(
            f"API request timed out after {request_timeout_seconds}s: {url}"
        ) from e
    except requests.RequestException as e:
        raise ETLExtractError(f"API request failed for {url}: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise ETLExtractError(f"API returned invalid JSON from {url}: {e}") from e

    if not isinstance(data, dict):
        raise ETLExtractError(f"Unexpected API response shape (expected object): {type(data).__name__}")

    rows = data.get("value", [])
    if not isinstance(rows, list):
        raise ETLExtractError(f"Unexpected API response: 'value' is not a list")

    logger.info("Fetched %s records", len(rows))
    return rows
