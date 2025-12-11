import pandas as pd
import numpy as np
from typing import Dict, Union

class TechnicalIndicators:
    """
    Standard Indicator Library ("The Lego Blocks")
    Optimized implementation using pandas/numpy for vectorization.
    """

    @staticmethod
    def sma(series: pd.Series, period: int = 20) -> float:
        """Simple Moving Average"""
        return series.rolling(window=period).mean().iloc[-1]

    @staticmethod
    def ema(series: pd.Series, period: int = 20) -> float:
        """Exponential Moving Average"""
        return series.ewm(span=period, adjust=False).mean().iloc[-1]

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> float:
        """Relative Strength Index"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, float]:
        """Moving Average Convergence Divergence"""
        exp1 = series.ewm(span=fast, adjust=False).mean()
        exp2 = series.ewm(span=slow, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            "macd": macd_line.iloc[-1],
            "signal": signal_line.iloc[-1],
            "histogram": histogram.iloc[-1]
        }

    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, float]:
        """Bollinger Bands"""
        sma = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        return {
            "upper": upper.iloc[-1],
            "middle": sma.iloc[-1],
            "lower": lower.iloc[-1]
        }

    @staticmethod
    def supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 7, multiplier: int = 3) -> Dict[str, Union[float, str]]:
        """
        SuperTrend Indicator
        Returns: {'value': float, 'direction': 'buy'|'sell'}
        """
        # Calculate ATR
        tr1 = pd.DataFrame(high - low)
        tr2 = pd.DataFrame(abs(high - close.shift(1)))
        tr3 = pd.DataFrame(abs(low - close.shift(1)))
        frames = [tr1, tr2, tr3]
        tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
        atr = tr.ewm(alpha=1/period).mean()

        # Calculate Basic Upper and Lower Bands
        hl2 = (high + low) / 2
        basic_upperband = hl2 + (multiplier * atr)
        basic_lowerband = hl2 - (multiplier * atr)

        # Simplified logic for last value (suitable for alert check)
        # Note: Full supertrend requires iteration, this is a simplified 'snapshot' check
        # For production, we'd implement the full recursive calculation if history is needed.
        # Here we return the basic components for the alert logic to decide.
        
        current_close = close.iloc[-1]
        current_upper = basic_upperband.iloc[-1]
        current_lower = basic_lowerband.iloc[-1]
        
        # Simple trend determination for current candle
        if current_close > current_upper:
            direction = "buy"
        elif current_close < current_lower:
            direction = "sell"
        else:
            direction = "neutral" 

        return {
            "upper": current_upper,
            "lower": current_lower,
            "direction": direction
        }

    @staticmethod
    def vwap(df: pd.DataFrame) -> float:
        """Volume Weighted Average Price (Intraday)"""
        v = df['volume']
        tp = (df['high'] + df['low'] + df['close']) / 3
        return (tp * v).cumsum() / v.cumsum()
