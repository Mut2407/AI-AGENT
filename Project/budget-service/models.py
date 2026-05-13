from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from database import Base
import datetime

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    amount = Column(Float)
    category = Column(String, index=True)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    tags = Column(JSON) 
    note = Column(String, nullable=True)
    recurring_interval = Column(String, nullable=True)
    user_id = Column(Integer, index=True) # Không dùng ForeignKey nữa

class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    amount = Column(Float)
    category = Column(String, index=True)
    tags = Column(JSON)
    interval = Column(String)
    startDate = Column(DateTime)
    occurrences = Column(Integer)
    user_id = Column(Integer, index=True)