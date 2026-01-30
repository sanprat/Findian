import io
import logging
import base64
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yfinance as yf
from app.db.base import SessionLocal
from app.core.lookup import resolve_symbol

# Use Agg backend for non-interactive plotting (server-side)
matplotlib.use("Agg")

logger = logging.getLogger(__name__)

def generate_stock_chart(symbol: str, period: str = "1mo") -> str:
    """
    Generates a stock price & volume chart and returns it as a Base64 string.
    """
    try:
        # Smart Resolve
        db = SessionLocal()
        try:
             resolved_symbol = resolve_symbol(db, symbol)
        finally:
             db.close()
        
        yf_symbol = f"{resolved_symbol}.NS"
        
        # Fetch Data
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return ""

        # Create Plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
        
        # Price Chart (Top)
        ax1.plot(hist.index, hist["Close"], label="Close Price", color="#1f77b4", linewidth=2)
        ax1.set_title(f"{resolved_symbol} - Price Trend ({period})", fontsize=14, fontweight='bold')
        ax1.set_ylabel("Price (₹)")
        ax1.grid(True, linestyle="--", alpha=0.6)
        ax1.legend()
        
        # Volume Chart (Bottom)
        colors = ['red' if row['Open'] > row['Close'] else 'green' for i, row in hist.iterrows()]
        ax2.bar(hist.index, hist["Volume"], color=colors, alpha=0.7)
        ax2.set_ylabel("Volume")
        ax2.grid(True, linestyle="--", alpha=0.3)
        
        # Format X-Axis
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Save to Buffer
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches='tight')
        buf.seek(0)
        
        # Encode to Base64
        image_base64 = base64.b64encode(buf.read()).decode("utf-8")
        
        # Cleanup
        plt.close(fig)
        buf.close()
        
        return image_base64
        
    except Exception as e:
        logger.error(f"Chart Generation Error for {symbol}: {e}")
        return ""
