import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import (
    DEFAULT_FETCH_BACKOFF_FACTOR,
    DEFAULT_FETCH_MAX_RETRIES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_WHO_API_BASE_URL,
)
from app.errors import ETLExtractError
from app.logger import get_logger

logger = get_logger(__name__)

RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)


def create_http_session(max_retries: int, backoff_factor: float) -> requests.Session:
    """Build a requests session with urllib3 retries for transient API failures."""
    session = requests.Session()

    if max_retries > 0:
        retry = Retry(
            total=max_retries,
            connect=max_retries,
            read=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=RETRYABLE_STATUS_CODES,
            allowed_methods=frozenset(["GET"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

    return session


def fetch_page(
    skip: int = 0,
    top: int = DEFAULT_PAGE_SIZE,
    *,
    api_base_url: str = DEFAULT_WHO_API_BASE_URL,
    request_timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_FETCH_MAX_RETRIES,
    retry_backoff_factor: float = DEFAULT_FETCH_BACKOFF_FACTOR,
) -> list:
    url = f"{api_base_url}?$top={top}&$skip={skip}"

    logger.info(
        "Fetching data: skip=%s, top=%s (max_retries=%s, backoff=%s)",
        skip,
        top,
        max_retries,
        retry_backoff_factor,
    )

    session = create_http_session(max_retries, retry_backoff_factor)

    try:
        response = session.get(url, timeout=request_timeout_seconds)
        response.raise_for_status()
    except requests.Timeout as e:
        raise ETLExtractError(
            f"API request timed out after {request_timeout_seconds}s "
            f"({max_retries} retries): {url}"
        ) from e
    except requests.RequestException as e:
        raise ETLExtractError(
            f"API request failed after {max_retries} retries for {url}: {e}"
        ) from e
    finally:
        session.close()

    try:
        data = response.json()
    except ValueError as e:
        raise ETLExtractError(f"API returned invalid JSON from {url}: {e}") from e

    if not isinstance(data, dict):
        raise ETLExtractError(
            f"Unexpected API response shape (expected object): {type(data).__name__}"
        )

    rows = data.get("value", [])
    if not isinstance(rows, list):
        raise ETLExtractError("Unexpected API response: 'value' is not a list")

    logger.info("Fetched %s records", len(rows))
    return rows
