from pydantic import BaseModel, Field


class HealthMetricRecord(BaseModel):
    """Validated row ready for load into health_metrics."""

    country_code: str = Field(min_length=1, max_length=10)
    indicator: str = Field(min_length=1, max_length=50)
    year: int = Field(ge=1800, le=2100)
    value: float
