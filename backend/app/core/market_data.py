import os
import logging
import pyotp
from NorenRestApiPy.NorenApi import NorenApi

logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self):
        self.api = NorenApi(host='https://api.shoonya.com/NorenWClientTP/', websocket='wss://api.shoonya.com/NorenWSTP/')
        self.user_id = os.getenv("FINVASIA_USER_ID")
        self.password = os.getenv("FINVASIA_PASSWORD")
        self.token = os.getenv("FINVASIA_TOKEN")
        self.totp_key = os.getenv("FINVASIA_TOTP_KEY")
        self.vendor_code = os.getenv("FINVASIA_VENDOR_CODE")
        self.imei = os.getenv("FINVASIA_IMEI")
        self.is_connected = False

    def login(self):
        """
        Logs in to Finvasia using the credentials and auto-generated TOTP.
        """
        try:
            if not self.totp_key:
                logger.error("FINVASIA_TOTP_KEY is missing!")
                return False

            # 1. Generate TOTP
            totp = pyotp.TOTP(self.totp_key)
            current_otp = totp.now()

            # 2. Login
            ret = self.api.login(
                userid=self.user_id,
                password=self.password,
                twoFA=current_otp,
                vendor_code=self.vendor_code,
                api_secret=self.token,
                imei=self.imei
            )

            if ret and ret.get('stat') == 'Ok':
                self.is_connected = True
                logger.info(f"✅ Finvasia Login Successful. Token: {ret.get('susertoken')}")
                return True
            else:
                logger.error(f"❌ Finvasia Login Failed: {ret.get('emsg')}")
                return False

        except Exception as e:
            logger.error(f"❌ Login Critical Error: {str(e)}")
            return False

    def get_quote(self, symbol: str, exchange: str = "NSE"):
        """
        Fetch live quote (LTP) for a symbol.
        """
        if not self.is_connected:
            if not self.login():
                return None

        # Search for the scrip first to get token
        print(f"DEBUG: 🔍 Searching Finvasia for: {symbol}", flush=True)
        search = self.api.searchscrip(exchange=exchange, searchtext=symbol)
        
        # Retry with -EQ suffix if not found (Common Finvasia issue)
        if not search and not symbol.endswith("-EQ"):
             print(f"DEBUG: ⚠️ Exact match failed. Retrying with {symbol}-EQ...", flush=True)
             search = self.api.searchscrip(exchange=exchange, searchtext=f"{symbol}-EQ")
        
        if search and len(search) > 0:
            # Assume first match is correct (Improve this later)
            match = search[0]
            token = match['token']
            trading_symbol = match['tsym']
            print(f"DEBUG: ✅ Found Symbol: {trading_symbol} (Token: {token})", flush=True)
            
            # Get Quote
            # NorenApi uses different methods for Rest vs Websocket. 
            # For MVP, we use REST snapshot.
            quote = self.api.get_quotes(exchange=exchange, token=token)
            print(f"DEBUG: 📉 Raw Quote Response: {quote}", flush=True)
            
            if quote and quote.get('stat') == 'Ok':
                return {
                    "symbol": symbol,
                    "ltp": float(quote.get('lp', 0)),
                    "volume": int(quote.get('v', 0)),
                    "close": float(quote.get('c', 0)),
                    "high": float(quote.get('h', 0)),
                    "low": float(quote.get('l', 0)),
                    "open": float(quote.get('o', 0)),
                }
        
        # --- FAILOVER: YAHOO FINANCE (For Weekends & Holidays) ---
        # If Finvasia fails (Token not found), we fetch from Yahoo.
        print(f"DEBUG: ⚠️ Finvasia Failed. Rolling over to Yahoo Finance for {symbol}...", flush=True)
        try:
            import yfinance as yf
            # Step 1: Fetch Intraday 1m Data (For precise LTP)
            # Fetching 5 days to ensure we find the last trading session
            yf_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(yf_symbol)
            
            # Fetch BOTH Intraday (1m) and Daily (1d) data
            intraday_data = ticker.history(period="5d", interval="1m")
            daily_data = ticker.history(period="5d", interval="1d")
            
            if intraday_data.empty:
                # Fallback to BSE
                yf_symbol = f"{symbol}.BO"
                ticker = yf.Ticker(yf_symbol)
                intraday_data = ticker.history(period="5d", interval="1m")
                daily_data = ticker.history(period="5d", interval="1d")

            if not intraday_data.empty and not daily_data.empty:
                # 1. Get Precise LTP (Last Minute)
                last_tick = intraday_data.iloc[-1]
                ltp = float(last_tick["Close"])
                
                # 2. Get Daily Stats (Volume, High, Low, Open from Daily Candle)
                # Use the last COMPLETED day or current day
                last_day = daily_data.iloc[-1]
                
                # 3. Get Previous Close (for Change % calculation)
                # If we have at least 2 days of data, use -2. Else use Open.
                prev_close = last_day['Open']
                if len(daily_data) >= 2:
                    prev_close = daily_data.iloc[-2]['Close']

                print(f"DEBUG: ✅ Combined Yahoo Data -> LTP: {ltp}, PrevClose: {prev_close}, H/L: {last_day['High']}/{last_day['Low']}", flush=True)
                
                return {
                     "symbol": symbol,
                     "ltp": round(ltp, 2),
                     "volume": int(last_day["Volume"]),
                     "close": round(float(prev_close), 2),  # Use PrevClose so Bot calculates Diff correctly
                     "high": round(float(last_day["High"]), 2),
                     "low": round(float(last_day["Low"]), 2),
                     "open": round(float(last_day["Open"]), 2),
                     "status": "FALLBACK_YF_HYBRID"
                }
        except Exception as e:
            print(f"DEBUG: ❌ Yahoo Finance Failed: {str(e)}", flush=True)

        # --- LAST RESORT: MOCK DATA ---
        import random
        base = random.uniform(500, 3000)
        ltp = base * random.uniform(0.98, 1.02)
        
        return {
             "symbol": symbol,
             "ltp": round(ltp, 2),
             "volume": random.randint(50000, 500000),
             "close": round(base, 2),
             "high": round(ltp * 1.01, 2),
             "low": round(ltp * 0.99, 2),
             "open": round(base * 1.005, 2),
             "status": "SIMULATED"
        }
