import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class MarketDataService:
    def __init__(self):
        self.is_connected = True
        self.smart_api = None  # Will be injected from main.py

    def set_smart_api(self, smart_api):
        """Inject SmartConnect instance from authenticated session"""
        self.smart_api = smart_api
        logger.info("✅ SmartAPI injected into MarketDataService")

    def login(self):
        """
        Login handled by SmartApiAuth. This is a compatibility method.
        """
        logger.info("✅ MarketDataService initialized (using SmartAPI)")
        return True

    def get_quote(self, symbol: str, exchange: str = "NSE") -> Optional[Dict]:
        """
        Fetch live quote (LTP) for a symbol using SmartAPI.
        Falls back to yfinance if SmartAPI not available.
        """
        from app.core.symbol_tokens import get_token, resolve_alias
        
        # Resolve Alias (e.g., UBI -> UNIONBANK)
        symbol = resolve_alias(symbol)

        # Try SmartAPI first
        if self.smart_api:
            try:
                token = get_token(symbol)
                if not token:
                    logger.warning(f"⚠️ Token not found for {symbol}, falling back to yfinance")
                    return self._get_quote_yfinance(symbol)
                
                # Use SmartAPI ltpData
                exchange_type = "NSE"
                trading_symbol = symbol
                response = self.smart_api.ltpData(exchange_type, trading_symbol, token)
                
                if response and response.get('status'):
                    data = response.get('data', {})
                    ltp = data.get('ltp', 0)
                    
                    # Return basic quote with LTP
                    # Note: Full OHLC requires historical data API
                    return {
                        "symbol": symbol,
                        "ltp": round(float(ltp), 2),
                        "volume": 0,  # Not available in ltpData
                        "close": round(float(ltp), 2),
                        "high": round(float(ltp), 2),
                        "low": round(float(ltp), 2),
                        "open": round(float(ltp), 2),
                    }
                        
            except Exception as e:
                logger.error(f"❌ SmartAPI Failed for {symbol}: {str(e)}")
                return self._get_quote_yfinance(symbol)
        
        # Fallback to yfinance if SmartAPI not available
        return self._get_quote_yfinance(symbol)

    def _get_quote_yfinance(self, symbol: str) -> Optional[Dict]:
        """Fallback: Fetch quote using yfinance (for unsupported symbols)"""
        try:
            import yfinance as yf
            
            # Resolve Alias again if called directly (redundant but safe)
            from app.core.symbol_tokens import resolve_alias
            symbol = resolve_alias(symbol)

            yf_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(yf_symbol)

            intraday_data = ticker.history(period="5d", interval="1m")
            daily_data = ticker.history(period="5d", interval="1d")

            if intraday_data.empty:
                yf_symbol = f"{symbol}.BO"
                ticker = yf.Ticker(yf_symbol)
                intraday_data = ticker.history(period="5d", interval="1m")
                daily_data = ticker.history(period="5d", interval="1d")

            if not intraday_data.empty and not daily_data.empty:
                last_tick = intraday_data.iloc[-1]
                ltp = float(last_tick["Close"])
                last_day = daily_data.iloc[-1]
                prev_close = last_day["Open"]

                if len(daily_data) >= 2:
                    prev_close = daily_data.iloc[-2]["Close"]

                return {
                    "symbol": symbol,
                    "ltp": round(ltp, 2),
                    "volume": int(last_day["Volume"]),
                    "close": round(float(prev_close), 2),
                    "high": round(float(last_day["High"]), 2),
                    "low": round(float(last_day["Low"]), 2),
                    "open": round(float(last_day["Open"]), 2),
                }
        except Exception as e:
            logger.error(f"❌ yfinance Fallback Failed for {symbol}: {str(e)}")

        return None

    def get_historical_data(self, symbol: str, period: str = "1mo") -> list:
        """
        Fetch historical close prices for a symbol.
        Uses yfinance for now (SmartAPI historical requires different API)
        """
        try:
            import yfinance as yf

            yf_symbol = (
                f"{symbol}.NS" if not symbol.endswith((".NS", ".BO")) else symbol
            )

            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period=period)

            if hist.empty:
                return []

            results = []
            for date, row in hist.iterrows():
                results.append(
                    {"date": date.strftime("%Y-%m-%d"), "close": float(row["Close"])}
                )

            return results

        except Exception as e:
            logger.error(f"Historical Data Fetch Error for {symbol}: {e}")
            return []

    def get_fundamentals(self, symbol: str) -> Optional[Dict]:
        """
        Fetch fundamental data (P/E, ROE, etc.) using yfinance.
        """
        try:
            import yfinance as yf
            from app.core.symbol_tokens import resolve_alias
            
            symbol = resolve_alias(symbol)
            yf_symbol = f"{symbol}.NS"
            
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            
            # Extract key metrics
            data = {
                "symbol": symbol,
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "roe": info.get("returnOnEquity"), # decimal (0.15 = 15%)
                "book_value": info.get("bookValue"),
                "dividend_yield": info.get("dividendYield"),
                "sector": info.get("sector"),
                "industry": info.get("industry")
            }
            
            return data
            
        except Exception as e:
            logger.error(f"Fundamentals Fetch Error for {symbol}: {e}")
            return None
    def get_analysis(self, symbol: str) -> Optional[Dict]:
        """
        Analyze stock for volume trends, breakouts, and price action.
        """
        try:
            import yfinance as yf
            import pandas as pd
            from app.core.symbol_tokens import resolve_alias
            
            symbol = resolve_alias(symbol)
            yf_symbol = f"{symbol}.NS"
            
            # Fetch 1 month of data
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period="1mo")
            
            if hist.empty or len(hist) < 5:
                return {"error": "Not enough data"}
                
            # Current Data
            last_day = hist.iloc[-1]
            prev_day = hist.iloc[-2]
            
            # Volume Analysis
            msg_vol = ""
            vol_avg_10 = hist["Volume"].tail(10).mean()
            curr_vol = last_day["Volume"]
            
            if curr_vol > (vol_avg_10 * 2):
                msg_vol = "Volume Explosion! (2x Average)"
            elif curr_vol > (vol_avg_10 * 1.5):
                msg_vol = "High Volume (1.5x Average)"
            elif curr_vol < (vol_avg_10 * 0.5):
                msg_vol = "Low Volume"
            else:
                msg_vol = "Average Volume"
                
            # Trend Analysis (Simple MA)
            ma_20 = hist["Close"].tail(20).mean() if len(hist) >= 20 else hist["Close"].mean()
            trend = "BULLISH" if last_day["Close"] > ma_20 else "BEARISH"
            
            # Percent Change
            close = last_day["Close"]
            prev_close = prev_day["Close"]
            change_pct = ((close - prev_close) / prev_close) * 100
            
            return {
                "symbol": symbol,
                "price": round(close, 2),
                "change_percent": round(change_pct, 2),
                "volume": int(curr_vol),
                "avg_volume": int(vol_avg_10),
                "vol_status": msg_vol,
                "trend": trend,
                "ma_20": round(ma_20, 2)
            }
            
        except Exception as e:
            logger.error(f"Analysis Error for {symbol}: {e}")
            return None
