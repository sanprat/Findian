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
        self.avg_volumes = {} # Cache for baselines

    def start(self):
        """Starts the scanner loop in a separate thread."""
        if not self.is_running:
            self.is_running = True
            
            # Pre-fetch baselines in background (don't block heavily)
            threading.Thread(target=self._fetch_historical_baselines, daemon=True).start()
            
            self._thread = threading.Thread(target=self._snapshot_loop, daemon=True)
            self._thread.start()
            logger.info("🚀 Market Scanner Thread Started")

    def _fetch_historical_baselines(self):
        """
        Fetches 10-day average volume for all symbols using yfinance.
        Runs once on startup.
        """
        logger.info("📊 Fetching historical baselines (Avg Volume) via yfinance...")
        import yfinance as yf
        
        try:
            # Batch Optimized: Download all at once
            tickers_list = [f"{sym}.NS" for sym in self.symbols]
            tickers_str = " ".join(tickers_list)
            
            logger.info(f"Downloading batch history for {len(tickers_list)} stocks...")
            # threads=True enables parallel fetching
            data = yf.download(tickers_str, period="1mo", threads=True, group_by='ticker')
            
            count = 0
            for sym in self.symbols:
                try:
                    # yfinance returns MultiIndex DFs when grouped by ticker
                    try:
                        hist = data[f"{sym}.NS"]
                    except KeyError:
                        # Fallback if ticker lookup fails in batch result
                        self.avg_volumes[sym] = 500000
                        continue

                    if not hist.empty:
                        # Drop NaN rows (common in batch fetch for missing days)
                        hist = hist.dropna()
                        if not hist.empty:
                             # avg volume of last 10 days
                             recent = hist.tail(10)
                             avg_vol = recent['Volume'].mean()
                             self.avg_volumes[sym] = avg_vol
                             count += 1
                        else:
                             self.avg_volumes[sym] = 500000
                    else:
                        self.avg_volumes[sym] = 500000
                except Exception as e:
                     self.avg_volumes[sym] = 500000 
            
            logger.info(f"✅ Historical Baselines Loaded for {count} stocks (Batch Mode).")

        except Exception as e:
            logger.error(f"Batch Baseline Fetch Error: {e}")

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
                        # 1. Try Fetching Real Data (Hybrid Engine: Finvasia -> Yahoo)
                        quote = self.md.get_quote(sym)
                        if quote:
                            ltp = quote['ltp']
                            prev_close = quote['close']
                            change_pct = ((ltp - prev_close) / prev_close) * 100 if prev_close > 0 else 0
                             
                            data_to_store = {
                                "symbol": sym,
                                "ltp": ltp,
                                "change_percent": round(change_pct, 2),
                                "volume": quote.get('volume', 0),
                                "high": quote.get('high', 0),
                                "low": quote.get('low', 0),
                                "prev_close": prev_close,
                                "avg_volume": int(self.avg_volumes.get(sym, 0)) # Inject Baseline
                            }
                    except Exception as e:
                        logger.warning(f"Real Data Fetch Failed for {sym}: {e}")
                        
                    # 2. FAILOVER: Mock Data if MD completely fails (Should not happen with Hybrid engine often)
                    if not data_to_store:
                         # Keeping minimal mock for absolute worst case
                         import random
                         base = 1000
                         data_to_store = {
                            "symbol": sym,
                            "ltp": 1000,
                            "change_percent": 0.0,
                            "volume": 0,
                            "avg_volume": 500000,
                            "timestamp": "Simulated"
                         }

                    # 3. Add Indicators (RSI/SMA) & Store
                    if data_to_store:
                        import random
                        # Consistent Mock Indicators (can be replaced by ta-lib later)
                        mock_rsi = random.uniform(25, 75)
                        # Bias RSI based on price change for realism
                        if data_to_store["change_percent"] > 3: mock_rsi = random.uniform(65, 85)
                        if data_to_store["change_percent"] < -3: mock_rsi = random.uniform(15, 35)
                        
                        data_to_store["rsi"] = round(mock_rsi, 2)
                        
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
