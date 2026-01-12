"""
Fundamentals Service - Fetches and caches stock fundamentals in Redis
Used for guru screeners (Minervini, Lynch, Buffett)
"""
import logging
import threading
import time
import os
import redis

logger = logging.getLogger(__name__)


class FundamentalsService:
    def __init__(self, symbols: list):
        self.symbols = symbols
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.r = redis.from_url(redis_url, decode_responses=True)
        self.is_running = False
        self._thread = None
        
    def start(self):
        """Start background fundamentals refresh"""
        if not self.is_running:
            self.is_running = True
            # Delay fetch to not block startup (fetch after 30 seconds)
            threading.Thread(target=self._delayed_fetch, daemon=True).start()
            logger.info("📊 Fundamentals Service Started (will fetch in 30s)")
    
    def _delayed_fetch(self):
        """Wait 30 seconds then fetch fundamentals"""
        import time
        time.sleep(30)  # Don't block startup
        self._fetch_fundamentals()
        # Then schedule daily refresh
        self._daily_refresh_loop()
    
    def _daily_refresh_loop(self):
        """Refresh fundamentals every 24 hours"""
        while self.is_running:
            # Sleep until next refresh (24 hours)
            time.sleep(86400)  # 24 hours
            self._fetch_fundamentals()
    
    def _fetch_fundamentals(self):
        """Fetch fundamentals for all symbols and cache in Redis"""
        import yfinance as yf
        
        logger.info("📊 Fetching fundamentals for all stocks...")
        count = 0
        
        for sym in self.symbols:
            try:
                ticker = yf.Ticker(f"{sym}.NS")
                info = ticker.info
                
                if not info:
                    continue
                
                # Extract key fundamentals
                fundamentals = {
                    "pe": str(info.get("trailingPE", 0) or 0),
                    "roe": str(round((info.get("returnOnEquity", 0) or 0) * 100, 2)),
                    "de": str(info.get("debtToEquity", 0) or 0),
                    "peg": str(info.get("pegRatio", 0) or 0),
                    "market_cap": str(info.get("marketCap", 0) or 0),
                    "high_52w": str(info.get("fiftyTwoWeekHigh", 0) or 0),
                    "low_52w": str(info.get("fiftyTwoWeekLow", 0) or 0),
                    "dividend_yield": str(round((info.get("dividendYield", 0) or 0) * 100, 2)),
                    "book_value": str(info.get("bookValue", 0) or 0),
                    "current_ratio": str(info.get("currentRatio", 0) or 0),
                }
                
                # Store in Redis (same key as scanner uses)
                key = f"stock:{sym}"
                self.r.hset(key, mapping=fundamentals)
                count += 1
                
                # Small delay to avoid rate limiting
                time.sleep(0.3)
                
            except Exception as e:
                logger.debug(f"Fundamentals fetch failed for {sym}: {e}")
                continue
        
        logger.info(f"✅ Fundamentals cached for {count}/{len(self.symbols)} stocks")
    
    def get_fundamentals(self, symbol: str) -> dict:
        """Get cached fundamentals for a symbol"""
        key = f"stock:{symbol}"
        data = self.r.hgetall(key)
        return data if data else {}


# Guru Screener Criteria
GURU_SCREENERS = {
    "minervini": {
        "name": "Mark Minervini (SEPA)",
        "description": "Momentum stocks near 52-week highs",
        "criteria": {
            # Price within 25% of 52-week high
            # Price > 50% above 52-week low
            # RSI > 50 (momentum)
        }
    },
    "lynch": {
        "name": "Peter Lynch (PEG)",
        "description": "Growth at reasonable price",
        "criteria": {
            # P/E < 20
            # PEG < 1.5 (if available)
        }
    },
    "buffett": {
        "name": "Warren Buffett (Value)",
        "description": "Quality value stocks",
        "criteria": {
            # P/E < 15
            # ROE > 15%
            # D/E < 50
        }
    }
}


def apply_guru_filter(stock_data: dict, guru: str) -> bool:
    """Check if stock matches guru criteria"""
    try:
        ltp = float(stock_data.get("ltp", 0))
        pe = float(stock_data.get("pe", 0))
        roe = float(stock_data.get("roe", 0))
        de = float(stock_data.get("de", 0))
        high_52w = float(stock_data.get("high_52w", 0))
        low_52w = float(stock_data.get("low_52w", 0))
        rsi = float(stock_data.get("rsi", 50))
        
        if guru == "minervini":
            # SEPA: Near highs, momentum
            if high_52w > 0 and low_52w > 0:
                pct_from_high = ((high_52w - ltp) / high_52w) * 100
                pct_above_low = ((ltp - low_52w) / low_52w) * 100
                
                return (
                    pct_from_high <= 25 and  # Within 25% of 52w high
                    pct_above_low >= 30 and  # At least 30% above 52w low
                    rsi >= 50                 # Momentum positive
                )
                
        elif guru == "lynch":
            # PEG: Growth at reasonable price
            if pe > 0:
                return (
                    pe > 0 and pe < 20 and   # Reasonable P/E
                    roe > 10                  # Decent growth
                )
                
        elif guru == "buffett":
            # Value: Quality at discount
            if pe > 0:
                return (
                    pe > 0 and pe < 15 and   # Low P/E
                    roe > 15 and             # High ROE
                    de < 50                   # Low debt
                )
    except:
        pass
    
    return False
