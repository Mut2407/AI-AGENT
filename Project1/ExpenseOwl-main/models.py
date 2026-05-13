from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime, timezone
from database import Base

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    category = Column(String(50), index=True, nullable=False)
    description = Column(Text, nullable=True)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))