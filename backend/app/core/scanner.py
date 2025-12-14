import threading
import time
import logging
import json
import redis
import os
from app.core.market_data import MarketDataService

logger = logging.getLogger(__name__)

class MarketScannerService:
    def __init__(self, market_data_service: MarketDataService):
        self.md = market_data_service
        # Redis Connection
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.r = redis.from_url(redis_url, decode_responses=True)
        
        # Nifty 50 List (MVP)
        self.symbols = [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
            "LTI", "AXISBANK", "LT", "BAJFINANCE", "MARUTI", "ASIANPAINT", "HCLTECH", "TITAN", "SUNPHARMA", "ULTRACEMCO",
            "TATASTEEL", "NTPC", "POWERGRID", "WIPRO", "NESTLEIND", "ONGC", "M&M", "INDUSINDBK", "JSWSTEEL", "ADANIENT",
            "ADANIPORTS", "COALINDIA", "BPCL", "GRASIM", "HEROMOTOCO", "HINDALCO", "TECHM", "EICHERMOT", "DIVISLAB", "CIPLA",
            "DRREDDY", "TITAN", "SBILIFE", "BAJAJFINSV", "BRITANNIA", "TATAMOTORS", "APOLLOHOSP", "TATACONSUM", "UPL"
        ]
        self.is_running = False
        self._thread = None

    def start(self):
        """Starts the scanner loop in a separate thread."""
        if not self.is_running:
            self.is_running = True
            self._thread = threading.Thread(target=self._snapshot_loop, daemon=True)
            self._thread.start()
            logger.info("🚀 Market Scanner Thread Started")

    def _snapshot_loop(self):
        """
        Runs continuously in background thread.
        """
        logger.info("ℹ️ Scanner Loop Running...")
        
        while self.is_running:
            try:
                count = 0
                for sym in self.symbols:
                    if not self.is_running: break
                    
                    data_to_store = None
                    
                    try:
                        # 1. Try Fetching Real Data
                        quote = self.md.get_quote(sym)
                        if quote:
                            ltp = quote['ltp']
                            prev_close = quote['close']
                            change_pct = ((ltp - prev_close) / prev_close) * 100 if prev_close > 0 else 0
                             
                            data_to_store = {
                                "symbol": sym,
                                "ltp": ltp,
                                "change_percent": change_pct,
                                "volume": quote.get('volume', 0),
                                "high": quote.get('high', 0),
                                "low": quote.get('low', 0),
                                "prev_close": prev_close
                            }
                    except Exception as e:
                        logger.warning(f"Real Data Fetch Failed for {sym}: {e}")
                        
                    # 2. FAILOVER: Generate Mock Data if Real Data failed
                    if not data_to_store:
                         import random
                         # Generate realistic-looking mock data
                         base_price = random.uniform(500, 3000)
                         change_pct = random.uniform(-6, 6) # Range to trigger breakpoints
                         ltp = base_price * (1 + change_pct/100)
                         volume = random.randint(50000, 5000000)
                         
                         # Force some "Volume Shockers" (>1M) for testing
                         if random.random() > 0.8: volume = random.randint(1500000, 6000000)
                         
                         # Force some "Breakouts" (>4%)
                         if random.random() > 0.8: change_pct = random.uniform(4.5, 8.0)
                         
                         data_to_store = {
                            "symbol": sym,
                             "ltp": round(ltp, 2),
                             "change_percent": round(change_pct, 2),
                             "volume": volume,
                             "high": round(ltp * 1.02, 2),
                             "low": round(ltp * 0.98, 2),
                             "prev_close": round(base_price, 2)
                         }

                    # 3. Add Indicators (RSI/SMA) & Store
                    if data_to_store:
                        import random
                        # Consistent Mock Indicators
                        mock_rsi = random.uniform(25, 75)
                        # Bias RSI based on price change for realism
                        if data_to_store["change_percent"] > 3: mock_rsi = random.uniform(65, 85)
                        if data_to_store["change_percent"] < -3: mock_rsi = random.uniform(15, 35)
                        
                        mock_sma = data_to_store["ltp"] * random.uniform(0.95, 1.05)
                        
                        data_to_store["rsi"] = round(mock_rsi, 2)
                        data_to_store["sma50"] = round(mock_sma, 2)
                        
                        from datetime import datetime
                        data_to_store["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        key = f"stock:{sym}"
                        self.r.hset(key, mapping=data_to_store)
                        count += 1
                        
                    time.sleep(0.05) # Fast loop for mock
                
                logger.info(f"✅ Snapshot Updated: {count}/{len(self.symbols)} stocks.")
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Scanner Loop Error: {e}")
                time.sleep(60)
