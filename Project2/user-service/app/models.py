from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Date, Numeric
from sqlalchemy.orm import relationship
from database import Base
import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean

# Bảng User 
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    full_name = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    dob = Column(Date, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    


class UserConfig(Base):
    __tablename__ = "user_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, unique=True)
    currency = Column(String, default="usd")
    startDate = Column(Integer, default=1)
    categories = Column(JSON, default=["Food", "Transport", "Shopping", "Bills", "Entertainment"])

    financial_goal = Column(String, nullable=True, default="Chưa xác định")
    risk_tolerance = Column(String, nullable=True, default="Cân bằng")
    is_email_sync_enabled = Column(Boolean, default=False)

