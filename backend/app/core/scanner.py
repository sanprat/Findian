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
        
        # Nifty 50 List (Updated with correct symbols)
        self.symbols = [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
            "LTIM", "AXISBANK", "LT", "BAJFINANCE", "MARUTI", "ASIANPAINT", "HCLTECH", "TITAN", "SUNPHARMA", "ULTRACEMCO",
            "TATASTEEL", "NTPC", "POWERGRID", "WIPRO", "NESTLEIND", "ONGC", "M&M", "INDUSINDBK", "JSWSTEEL", "ADANIENT",
            "ADANIPORTS", "COALINDIA", "BPCL", "GRASIM", "HEROMOTOCO", "HINDALCO", "TECHM", "EICHERMOT", "DIVISLAB", "CIPLA",
            "DRREDDY", "SBILIFE", "BAJAJFINSV", "BRITANNIA", "TATAMOTORS", "APOLLOHOSP", "TATACONSUM", "UPL"
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
        import yfinance as yf
        import pandas as pd
        from datetime import datetime, time as dt_time
        
        while self.is_running:
            try:
                # Check if market is open (Mon-Fri, 9:15 AM - 3:30 PM IST)
                now = datetime.now()
                is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6
                market_start = dt_time(9, 15)
                market_end = dt_time(15, 30)
                is_market_hours = market_start <= now.time() <= market_end and not is_weekend
                
                # 1. BATCH FETCH HISTORY (For Indicators and weekend data)
                tickers_list = [f"{sym}.NS" for sym in self.symbols]
                tickers_str = " ".join(tickers_list)
                history_map = {}
                try:
                    # Optimized batch fetch
                    data = yf.download(tickers_str, period="1mo", threads=True, group_by='ticker', progress=False)
                    for sym in self.symbols:
                        try:
                            # yfinance logic to extract DF for symbol
                            try:
                                df = data[f"{sym}.NS"] if len(self.symbols) > 1 else data
                            except KeyError:
                                df = None
                                
                            if df is not None and not df.empty:
                                # Clean MultiIndex cols if present
                                if isinstance(df.columns, pd.MultiIndex):
                                    df.columns = df.columns.droplevel(1)
                                history_map[sym] = df
                        except: pass
                except Exception as e:
                    logger.warning(f"Batch History Fetch Failed: {e}")

                count = 0
                for sym in self.symbols:
                    if not self.is_running: break
                    
                    data_to_store = None
                    
                    try:
                        if is_market_hours:
                            # Market is open - use live quotes
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
                                    "avg_volume": int(self.avg_volumes.get(sym, 0))
                                }
                        else:
                            # Market is closed - use historical data (last 2 trading days)
                            if sym in history_map:
                                df = history_map[sym]
                                if len(df) >= 2:
                                    last_day = df.iloc[-1]
                                    prev_day = df.iloc[-2]
                                    
                                    ltp = float(last_day['Close'])
                                    prev_close = float(prev_day['Close'])
                                    change_pct = ((ltp - prev_close) / prev_close) * 100
                                    
                                    data_to_store = {
                                        "symbol": sym,
                                        "ltp": ltp,
                                        "change_percent": round(change_pct, 2),
                                        "volume": int(last_day['Volume']),
                                        "high": float(last_day['High']),
                                        "low": float(last_day['Low']),
                                        "prev_close": prev_close,
                                        "avg_volume": int(self.avg_volumes.get(sym, 0))
                                    }
                                    
                    except Exception as e:
                        logger.warning(f"Data Fetch Failed for {sym}: {e}")
                        
                    # 2. FAILOVER: Skip if data fetch fails
                    if not data_to_store:
                         continue

                    # 3. Add Indicators (RSI/SMA) & Store
                    if data_to_store:
                        # REAL RSI CALCULATION (Manual Implementation)
                        rsi_val = 50.0
                        if sym in history_map:
                             df = history_map[sym]
                             try:
                                 # Ensure we have enough data (RSI default 14)
                                 if len(df) > 14:
                                     # Calculate RSI
                                     # Update last row with latest LTP from Quote if available
                                     if data_to_store.get('ltp'):
                                         df_calc = df.copy() 
                                         # Update last close
                                         col_idx = df_calc.columns.get_loc('Close')
                                         df_calc.iloc[-1, col_idx] = data_to_store['ltp']
                                         
                                         # Manual RSI Logic (Wilder's Smoothing)
                                         delta = df_calc['Close'].diff()
                                         gain = (delta.where(delta > 0, 0)).fillna(0)
                                         loss = (-delta.where(delta < 0, 0)).fillna(0)
                                         
                                         avg_gain = gain.ewm(com=13, adjust=False).mean()
                                         avg_loss = loss.ewm(com=13, adjust=False).mean()
                                         
                                         rs = avg_gain / avg_loss
                                         df_calc['RSI_14'] = 100 - (100 / (1 + rs))

                                         val = df_calc['RSI_14'].iloc[-1]
                                         if not pd.isna(val):
                                             rsi_val = float(val)
                             except Exception as e:
                                 # logger.warning(f"RSI Calc Error {sym}: {e}")
                                 pass
                        
                        data_to_store["rsi"] = round(rsi_val, 2)
                        
                        from datetime import datetime
                        data_to_store["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        key = f"stock:{sym}"
                        self.r.hset(key, mapping=data_to_store)
                        count += 1
                        
                    time.sleep(0.05) # Fast loop
                
                logger.info(f"✅ Snapshot Updated: {count}/{len(self.symbols)} stocks.")
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Scanner Loop Error: {e}")
                time.sleep(60)
