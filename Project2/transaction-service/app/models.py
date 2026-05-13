from sqlalchemy import Column, Integer, String, DateTime, JSON, Numeric
from database import Base
import datetime

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    amount = Column(Numeric(15, 2))
    category = Column(String, index=True)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    tags = Column(JSON) 
    note = Column(String, nullable=True)
    recurring_interval = Column(String, nullable=True)
    
    # CHỈ LƯU ID BÌNH THƯỜNG, KHÔNG DÙNG FOREIGN KEY NỮA
    jar_id = Column(Integer, nullable=True) 
    
    # 🚀 ĐÃ SỬA: Chuyển Integer thành String
    user_id = Column(String, index=True) 

class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    amount = Column(Numeric(15, 2))
    category = Column(String, index=True)
    tags = Column(JSON)
    interval = Column(String) 
    startDate = Column(DateTime)
    occurrences = Column(Integer) 

    # 🚀 ĐÃ SỬA: Chuyển Integer thành String
    user_id = Column(String, index=True)