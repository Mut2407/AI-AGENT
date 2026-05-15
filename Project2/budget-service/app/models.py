from sqlalchemy import Column, Integer, String, Date, Numeric, DateTime
from database import Base
from datetime import datetime

class Budget(Base):
    __tablename__ = "budgets"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, index=True)
    limit_amount = Column(Numeric(15, 2)) 
    spent_amount = Column(Numeric(15, 2), default=0.0) # BẮT BUỘC có để lưu số đã tiêu
    period_type = Column(String, default="month")
    start_date = Column(Date)
    end_date = Column(Date) 
    
    # 🚀 ĐÃ SỬA: Chuyển Integer thành String
    user_id = Column(String, index=True)

class Jar(Base):
    __tablename__ = "jars"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String) 
    balance = Column(Numeric(15, 2), default=0.0)
    percent = Column(Numeric(15, 2), default=0.0) 
    goal_amount = Column(Numeric(15, 2), default=0.0) 
    color = Column(String, default="#8a2be2")        
    icon = Column(String, default="fa-piggy-bank") 
    
    # 🚀 ĐÃ SỬA: Chuyển Integer thành String
    user_id = Column(String, index=True)

class JarHistory(Base):
    __tablename__ = "jar_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    jar_id = Column(Integer)
    name = Column(String) 
    amount = Column(Numeric(15, 2))
    date = Column(DateTime, default=datetime.utcnow)