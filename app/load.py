from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.errors import ETLLoadError
from app.logger import get_logger
from app.models import HealthMetric

logger = get_logger(__name__)


def load_batch(records: list) -> None:
    if not records:
        logger.info("No records to load for this batch")
        return

    session: Session = SessionLocal()

    try:
        logger.info("Loading %s records", len(records))

        stmt = insert(HealthMetric).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["country_code", "indicator", "year", "sex"],
            set_={"value": stmt.excluded.value},
        )

        result = session.execute(stmt)
        session.commit()

        logger.info("Upsert load successful: %s rows affected", result.rowcount)

    except Exception as e:
        session.rollback()
        raise ETLLoadError(f"Database load failed: {e}") from e

    finally:
        session.close()
