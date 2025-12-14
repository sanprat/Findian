from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger
from datetime import datetime
from app.db.base import Base

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True) # Telegram User ID
    symbol = Column(String(50), index=True)      # e.g. "INFY-EQ"
    indicator = Column(String(50))               # "rsi", "price"
    operator = Column(String(10))                # ">", "<"
    threshold = Column(Float)                # 70.0
    status = Column(String(20), default="ACTIVE") # ACTIVE, TRIGGERED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True) # Telegram User ID
    symbol = Column(String(50), index=True)      # e.g. "TCS"
    quantity = Column(Integer)               # 10
    avg_price = Column(Float)                # 3000.0
    purchase_date = Column(DateTime, default=datetime.utcnow)
    # For Auto-Tracking later, we might need broker_id, but keeping simple for Manual now

class SavedScan(Base):
    __tablename__ = "saved_scans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True)
    name = Column(String(100))
    query = Column(String(500))  # The natural language query or JSON config
    created_at = Column(DateTime, default=datetime.utcnow)
