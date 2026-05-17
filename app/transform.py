from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from app.logger import get_logger
from app.schemas import HealthMetricRecord

logger = get_logger(__name__)


def transform_record(record: dict) -> Optional[Dict[str, Any]]:
    try:
        country = record.get("SpatialDim")
        year = record.get("TimeDim")
        indicator = record.get("IndicatorCode")
        # WHOSIS_000001: API field Dim1 → sex (e.g. SEX_MLE, SEX_FMLE, SEX_BTSX)
        sex = record.get("Dim1")
        value = record.get("NumericValue")

        if not country or not year or not sex or value is None:
            logger.warning("Skipping invalid record: %s", record)
            return None

        return HealthMetricRecord(
            country_code=str(country),
            indicator=str(indicator),
            year=int(year),
            sex=str(sex),
            value=float(value),
        ).model_dump()

    except ValidationError as e:
        logger.warning("Validation failed: %s | record=%s", e.errors(), record)
        return None
    except (TypeError, ValueError) as e:
        logger.error("Transform failed: %s | record=%s", e, record)
        return None


def transform_batch(records: List[dict]) -> List[dict]:
    deduped: Dict[tuple, Dict[str, Any]] = {}
    duplicate_count = 0

    for record in records:
        transformed = transform_record(record)
        if not transformed:
            continue

        key = (
            transformed["country_code"],
            transformed["indicator"],
            transformed["year"],
            transformed["sex"],
        )
        if key in deduped:
            duplicate_count += 1
        deduped[key] = transformed

    if duplicate_count:
        logger.warning(
            "Dropped %s duplicate keys within batch (kept latest value per key)",
            duplicate_count,
        )

    cleaned = list(deduped.values())
    logger.info("Transformed %s valid records out of %s", len(cleaned), len(records))
    return cleaned
