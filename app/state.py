import json
from pathlib import Path

from app.errors import ETLStateError
from app.logger import get_logger

logger = get_logger(__name__)

STATE_FILE = Path("state.json")


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"skip": 0}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ETLStateError(f"Could not read checkpoint file {STATE_FILE}: {e}") from e

    skip = state.get("skip")
    if not isinstance(skip, int) or skip < 0:
        raise ETLStateError(
            f"Invalid checkpoint in {STATE_FILE}: expected non-negative integer 'skip', got {skip!r}"
        )

    return {"skip": skip}


def save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except OSError as e:
        raise ETLStateError(f"Could not write checkpoint file {STATE_FILE}: {e}") from e

    logger.debug("Checkpoint saved: skip=%s", state.get("skip"))
