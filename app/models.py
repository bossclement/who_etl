from sqlalchemy import Column, Float, Integer, String, UniqueConstraint

from app.db import Base


class HealthMetric(Base):
    __tablename__ = "health_metrics"

    id = Column(Integer, primary_key=True, index=True)
    country_code = Column(String(10), index=True)
    indicator = Column(String(50), index=True)
    year = Column(Integer, index=True)
    sex = Column(String(20), index=True)
    value = Column(Float)

    __table_args__ = (
        UniqueConstraint("country_code", "indicator", "year", "sex"),
    )

    def __repr__(self):
        return (
            f"<HealthMetric {self.country_code} {self.indicator} "
            f"{self.year} {self.sex} {self.value}>"
        )
