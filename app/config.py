from dataclasses import dataclass
from typing import Optional

DEFAULT_WHO_API_BASE_URL = "https://ghoapi.azureedge.net/api/WHOSIS_000001"
DEFAULT_PAGE_SIZE = 100
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_FETCH_MAX_RETRIES = 3
DEFAULT_FETCH_BACKOFF_FACTOR = 1.0


@dataclass
class ETLConfig:
    api_base_url: str = DEFAULT_WHO_API_BASE_URL
    page_size: int = DEFAULT_PAGE_SIZE
    request_timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS
    fetch_max_retries: int = DEFAULT_FETCH_MAX_RETRIES
    fetch_backoff_factor: float = DEFAULT_FETCH_BACKOFF_FACTOR
    skip: Optional[int] = None
    reset: bool = False
    max_batches: Optional[int] = None
