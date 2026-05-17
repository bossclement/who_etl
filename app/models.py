from app.db import Base
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy import UniqueConstraint

class HealthMetric(Base):
    __tablename__ = "health_metrics"

    id = Column(Integer, primary_key=True, index=True)
    country_code = Column(String(10), index=True)
    indicator = Column(String(50), index=True)
    year = Column(Integer, index=True)
    value = Column(Float)

    __table_args__ = (
        UniqueConstraint("country_code", "indicator", "year"),
    )

    def __repr__(self):
        return f"<HealthMetric {self.country_code} {self.indicator} {self.year} {self.value}>"