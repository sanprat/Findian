from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger, ForeignKey
from datetime import datetime
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    subscription_tier = Column(String(20), default="FREE") # FREE, PRO, PREMIUM
    subscription_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

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

class TradeHistory(Base):
    __tablename__ = "trade_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"))
    symbol = Column(String(20))
    quantity = Column(Integer)
    price = Column(Float)
    trade_type = Column(String(10)) # BUY, SELL
    realized_pnl = Column(Float, nullable=True) # Only for SELL
    trade_date = Column(DateTime, default=datetime.utcnow)

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
