import os
import logging

logger = logging.getLogger(__name__)


class MarketDataService:
    def __init__(self):
        self.is_connected = True

    def login(self):
        """
        No login required for yfinance. Always returns True.
        """
        logger.info("✅ yfinance initialized successfully (no credentials needed)")
        return True

    def get_quote(self, symbol: str, exchange: str = "NSE"):
        """
        Fetch live quote (LTP) for a symbol using yfinance.
        """
        try:
            import yfinance as yf

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
            logger.error(f"❌ Yahoo Finance Failed for {symbol}: {str(e)}")

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
            "status": "SIMULATED",
        }

    def get_historical_data(self, symbol: str, period: str = "1mo") -> list:
        """
        Fetch historical close prices for a symbol using yfinance.
        Returns list of dicts: [{'date': 'YYYY-MM-DD', 'close': 123.45}, ...]
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
