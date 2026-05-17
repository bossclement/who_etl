import sys

from app.cli import parse_config
from app.config import ETLConfig
from app.errors import ETLError, ETLExtractError, ETLLoadError, ETLStateError
from app.extract import fetch_page
from app.load import load_batch
from app.logger import get_logger
from app.state import load_state, save_state
from app.transform import transform_batch

logger = get_logger(__name__)


def _resolve_skip(config: ETLConfig) -> int:
    if config.reset:
        save_state({"skip": 0})
        logger.info("Checkpoint reset to skip=0")
        return 0

    if config.skip is not None:
        logger.info("Using skip=%s from CLI (overrides state.json for this run)", config.skip)
        return config.skip

    return load_state()["skip"]


def run_pipeline(config: ETLConfig) -> None:
    skip = _resolve_skip(config)
    batches_run = 0

    if skip > 0:
        logger.info("Resuming from skip=%s", skip)
    else:
        logger.info("Starting pipeline from the beginning")

    logger.info(
        "Config: api_url=%s page_size=%s timeout=%ss max_batches=%s",
        config.api_base_url,
        config.page_size,
        config.request_timeout_seconds,
        config.max_batches if config.max_batches is not None else "unlimited",
    )

    while True:
        if config.max_batches is not None and batches_run >= config.max_batches:
            logger.info("Reached --max-batches=%s; stopping", config.max_batches)
            break

        try:
            raw = fetch_page(
                skip,
                config.page_size,
                api_base_url=config.api_base_url,
                request_timeout_seconds=config.request_timeout_seconds,
            )
        except ETLExtractError:
            logger.exception("Extract step failed; checkpoint not advanced (skip=%s)", skip)
            raise

        if not raw:
            logger.info("No more data. Pipeline complete.")
            break

        transformed = transform_batch(raw)

        try:
            load_batch(transformed)
        except ETLLoadError:
            logger.exception("Load step failed; checkpoint not advanced (skip=%s)", skip)
            raise

        skip += config.page_size
        save_state({"skip": skip})
        batches_run += 1

        logger.info("Checkpoint saved: skip=%s", skip)


def main(argv: list = None) -> int:
    config = parse_config(argv)

    try:
        run_pipeline(config)
    except ETLStateError as e:
        logger.error("State error: %s", e)
        return 1
    except ETLExtractError as e:
        logger.error("Extract error: %s", e)
        return 1
    except ETLLoadError as e:
        logger.error("Load error: %s", e)
        return 1
    except ETLError as e:
        logger.error("Pipeline error: %s", e)
        return 1
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        return 130

    logger.info("Pipeline finished successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
