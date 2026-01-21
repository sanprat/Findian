from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger, ForeignKey, Text, Boolean, Date, JSON, Index
from datetime import datetime
from app.db.base import Base

# --- Core Tables ---

class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), unique=True, index=True)  # e.g., RELIANCE-EQ
    token = Column(String(50), unique=True, index=True)   # Angel One Token
    name = Column(String(255))
    exchange = Column(String(20), default="NSE")
    sector = Column(String(100), index=True)
    industry = Column(String(100))
    market_cap = Column(BigInteger)
    is_active = Column(Boolean, default=True)

class DailyOHLCV(Base):
    __tablename__ = "daily_ohlcv"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), ForeignKey("stocks.symbol"), index=True)
    date = Column(Date, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)
    turnover = Column(Float)
    
    __table_args__ = (Index('idx_symbol_date', 'symbol', 'date', unique=True),)

class Intraday1Min(Base):
    __tablename__ = "intraday_1min"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), ForeignKey("stocks.symbol"), index=True)
    timestamp = Column(DateTime, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)

    __table_args__ = (Index('idx_intra_symbol_time', 'symbol', 'timestamp', unique=True),)

class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), ForeignKey("stocks.symbol"), index=True)
    date = Column(Date, index=True)
    sma_20 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    sma_200 = Column(Float, nullable=True)
    rsi_14 = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    bb_upper = Column(Float, nullable=True)
    bb_middle = Column(Float, nullable=True)
    bb_lower = Column(Float, nullable=True)
    resistance_1 = Column(Float, nullable=True)
    support_1 = Column(Float, nullable=True)
    week_52_high = Column(Float, nullable=True)
    week_52_low = Column(Float, nullable=True)
    avg_volume_20 = Column(Float, nullable=True)
    
    __table_args__ = (Index('idx_tech_symbol_date', 'symbol', 'date', unique=True),)

class FundamentalData(Base):
    __tablename__ = "fundamental_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), ForeignKey("stocks.symbol"), unique=True)
    pe_ratio = Column(Float, index=True)
    pb_ratio = Column(Float)
    roe = Column(Float, index=True)
    debt_to_equity = Column(Float)
    dividend_yield = Column(Float)
    market_cap = Column(BigInteger)
    eps = Column(Float)
    book_value = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow)

# --- User & Alert Tables ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    subscription_tier = Column(String(50), default="FREE")
    created_at = Column(DateTime, default=datetime.utcnow)

class UserWatchlist(Base):
    __tablename__ = "user_watchlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    symbol = Column(String(50), ForeignKey("stocks.symbol"), index=True)
    alert_type = Column(String(50)) # breakout, price_target, volume
    alert_conditions = Column(JSON) # {"target": 1500, "operator": ">"}
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index('idx_watchlist_user_symbol', 'user_id', 'symbol'),)

class UserFeedback(Base):
    """Stores user feedback and issues."""
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    category = Column(String(50)) # ISSUE, FEEDBACK
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    symbol = Column(String(50), index=True)
    alert_type = Column(String(50))
    trigger_price = Column(Float)
    trigger_volume = Column(BigInteger)
    metadata_info = Column(JSON, nullable=True) # Rename metadata to metadata_info to avoid conflict
    delivered_at = Column(DateTime, default=datetime.utcnow, index=True)
    was_read = Column(Boolean, default=False)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    symbol = Column(String(50), index=True)
    indicator = Column(String(50))  # price, rsi, volume, etc.
    operator = Column(String(20))   # >, <, crossover, etc.
    threshold = Column(Float)
    status = Column(String(20), default="ACTIVE", index=True)  # ACTIVE, TRIGGERED, EXPIRED
    created_at = Column(DateTime, default=datetime.utcnow)

class TradeHistory(Base):
    __tablename__ = "trade_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    symbol = Column(String(50), index=True)
    trade_type = Column(String(10))  # BUY, SELL
    quantity = Column(Integer)
    price = Column(Float)
    trade_date = Column(DateTime, default=datetime.utcnow)
    realized_pnl = Column(Float, nullable=True)

class Portfolio(Base):
    """User portfolio holdings - tracks stock positions."""
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    symbol = Column(String(50), index=True)
    quantity = Column(Integer)
    avg_price = Column(Float)
    purchase_date = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (Index('idx_portfolio_user_symbol', 'user_id', 'symbol'),)

class SavedScan(Base):
    """User-saved custom screening queries."""
    __tablename__ = "saved_scans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    name = Column(String(100))
    query = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (Index('idx_saved_scan_user', 'user_id'),)

# --- Scanner & System Tables ---

class ScannerResult(Base):
    __tablename__ = "scanner_results"

    id = Column(Integer, primary_key=True, index=True)
    scan_type = Column(String(50), index=True) # momentum, buffett
    symbol = Column(String(50), index=True)
    score = Column(Float)
    metadata_info = Column(JSON, nullable=True)
    scan_date = Column(Date, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AIAnalysisCache(Base):
    __tablename__ = "ai_analysis_cache"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), index=True)
    query_type = Column(String(50))
    query_hash = Column(String(64), index=True)
    analysis_text = Column(Text)
    analysis_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, index=True)

class WebSocketState(Base):
    __tablename__ = "websocket_state"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String(50))
    connection_id = Column(Integer)
    subscribed_tokens = Column(JSON)
    is_active = Column(Boolean, default=False)
    last_ping = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    log_level = Column(String(20))
    module = Column(String(50))
    message = Column(Text)
    metadata_info = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ApiCallLog(Base):
    __tablename__ = "api_call_logs"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String(50))
    endpoint = Column(String(100))
    method = Column(String(10))
    status_code = Column(Integer)
    response_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
