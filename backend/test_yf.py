import yfinance as yf
ticker = yf.Ticker("RELIANCE.NS")
# Fetch 1 minute data for the last 5 days match
data = ticker.history(period="5d", interval="1m")
print(data.tail(10))
if not data.empty:
    last_idx = data.index[-1]
    print(f"\nLast Timestamp: {last_idx}")
    print(f"Close Price: {data.iloc[-1]['Close']}")
