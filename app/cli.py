import argparse

from app.config import (
    DEFAULT_FETCH_BACKOFF_FACTOR,
    DEFAULT_FETCH_MAX_RETRIES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_WHO_API_BASE_URL,
    ETLConfig,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract WHO GHO data, transform, and load into PostgreSQL.",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_WHO_API_BASE_URL,
        help=f"WHO OData API endpoint (default: {DEFAULT_WHO_API_BASE_URL})",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        metavar="N",
        help=f"Records per API page / batch (default: {DEFAULT_PAGE_SIZE})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        metavar="SEC",
        help=f"HTTP request timeout in seconds (default: {DEFAULT_REQUEST_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_FETCH_MAX_RETRIES,
        metavar="N",
        help=f"Max retries per API request on transient errors (default: {DEFAULT_FETCH_MAX_RETRIES})",
    )
    parser.add_argument(
        "--retry-backoff",
        type=float,
        default=DEFAULT_FETCH_BACKOFF_FACTOR,
        metavar="SEC",
        help=(
            "Backoff factor between retries; delay grows as "
            f"factor * 2^attempt (default: {DEFAULT_FETCH_BACKOFF_FACTOR})"
        ),
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=None,
        metavar="N",
        help="Start extract at this OData $skip offset (overrides state.json for this run)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset checkpoint to skip=0 before running",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N batches (useful for debugging)",
    )
    return parser


def parse_config(argv: list = None) -> ETLConfig:
    args = build_parser().parse_args(argv)

    if args.page_size < 1:
        build_parser().error("--page-size must be at least 1")
    if args.timeout < 1:
        build_parser().error("--timeout must be at least 1")
    if args.skip is not None and args.skip < 0:
        build_parser().error("--skip must be non-negative")
    if args.max_batches is not None and args.max_batches < 1:
        build_parser().error("--max-batches must be at least 1")
    if args.max_retries < 0:
        build_parser().error("--max-retries must be non-negative")
    if args.retry_backoff < 0:
        build_parser().error("--retry-backoff must be non-negative")
    if args.reset and args.skip is not None:
        build_parser().error("Use either --reset or --skip, not both")

    return ETLConfig(
        api_base_url=args.api_url,
        page_size=args.page_size,
        request_timeout_seconds=args.timeout,
        fetch_max_retries=args.max_retries,
        fetch_backoff_factor=args.retry_backoff,
        skip=args.skip,
        reset=args.reset,
        max_batches=args.max_batches,
    )
