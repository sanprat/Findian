import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.db.models import Stock, DailyOHLCV, FundamentalData, TechnicalIndicator
from datetime import date, timedelta

logger = logging.getLogger(__name__)

class ScannerEngine:
    """
    Advanced Scanner running on MySQL HeatWave (or standard MySQL).
    Executes complex analytical queries.
    """
    def __init__(self, db: Session):
        self.db = db

    def scan_momentum(self, min_volume=100000, rsi_threshold=60):
        """
        Momentum Scan:
        - Price > SMA 20
        - RSI > 60
        - Volume > Avg Vol 20
        """
        try:
            # Join Stock, TechnicalIndicator
            results = (
                self.db.query(Stock.symbol, Stock.name, TechnicalIndicator.rsi_14, TechnicalIndicator.sma_20, DailyOHLCV.close)
                .join(TechnicalIndicator, Stock.symbol == TechnicalIndicator.symbol)
                .join(DailyOHLCV, Stock.symbol == DailyOHLCV.symbol)
                .filter(
                    TechnicalIndicator.rsi_14 > rsi_threshold,
                    DailyOHLCV.volume > min_volume,
                    DailyOHLCV.close > TechnicalIndicator.sma_20,
                    DailyOHLCV.date == date.today() # Caution: Ensure data is updated for 'today'
                )
                .order_by(desc(TechnicalIndicator.rsi_14))
                .limit(20)
                .all()
            )
            return [
                {"symbol": r.symbol, "name": r.name, "rsi": r.rsi_14, "price": r.close, "signal": "Momentum"}
                for r in results
            ]
        except Exception as e:
            logger.error(f"Momentum Scan Error: {e}")
            return []

    def scan_buffett(self):
        """
        Warren Buffett Style:
        - ROE > 15
        - Debt to Equity < 0.5
        - Profit Margin (implied high)
        """
        try:
            results = (
                self.db.query(Stock.symbol, Stock.name, FundamentalData.roe, FundamentalData.debt_to_equity)
                .join(FundamentalData, Stock.symbol == FundamentalData.symbol)
                .filter(
                    FundamentalData.roe > 15,
                    FundamentalData.debt_to_equity < 0.5
                )
                .order_by(desc(FundamentalData.roe))
                .limit(20)
                .all()
            )
            return [
                {"symbol": r.symbol, "name": r.name, "roe": r.roe, "debt_eq": r.debt_to_equity, "signal": "Buffett Value"}
                for r in results
            ]
        except Exception as e:
            logger.error(f"Buffett Scan Error: {e}")
            return []

    def scan_breakout(self, tolerance_pct=0.02):
        """
        Breakout Scan:
        - Price within 2% of 52-Week High
        - High Volume (handled by real-time engine usually, but here for EOD)
        """
        try:
            results = (
                self.db.query(Stock.symbol, Stock.name, DailyOHLCV.close, TechnicalIndicator.week_52_high)
                .join(TechnicalIndicator, Stock.symbol == TechnicalIndicator.symbol)
                .join(DailyOHLCV, Stock.symbol == DailyOHLCV.symbol)
                .filter(
                    DailyOHLCV.date == date.today(),
                    DailyOHLCV.close >= (TechnicalIndicator.week_52_high * (1 - tolerance_pct))
                )
                .all()
            )
            return [
                {"symbol": r.symbol, "name": r.name, "price": r.close, "near_high": r.week_52_high, "signal": "Near Breakout"}
                for r in results
            ]
        except Exception as e:
            logger.error(f"Breakout Scan Error: {e}")
            return []
