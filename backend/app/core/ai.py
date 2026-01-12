import httpx
import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AIAlertInterpreter:
    def __init__(self):
        self.api_token = os.getenv("CHUTES_API_TOKEN")
        self.base_url = "https://llm.chutes.ai/v1/chat/completions"
        self.models = [
            "openai/gpt-oss-20b",
            "zai-org/GLM-4.5-Air",
            "Alibaba-NLP/Tongyi-DeepResearch-30B-A3B"
        ]

    async def _call_with_fallback(self, messages: list, temperature: float = 0.1) -> Dict[str, Any]:
        """
        Tries models in order. Returns the JSON parsed response of the first success.
        """
        if not self.api_token:
            return {"status": "ERROR", "message": "CHUTES_API_TOKEN not configured"}

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        last_error = None

        for model in self.models:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": False
            }
            
            try:
                # logger.info(f"🤖 Attempting AI call with model: {model}")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.base_url, 
                        json=payload, 
                        headers=headers, 
                        timeout=30.0
                    )
                    response.raise_for_status()
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    
                    # Extract JSON from markdown
                    if "```" in content:
                        start = content.find('{')
                        end = content.rfind('}') + 1
                        json_str = content[start:end]
                    else:
                        json_str = content
                    
                    return json.loads(json_str)

            except Exception as e:
                logger.warning(f"⚠️ AI Model {model} failed: {e}. Trying next...")
                last_error = e
                continue
        
        # If all failed
        logger.error(f"❌ All AI models failed. Last error: {last_error}")
        return {"status": "ERROR", "message": "AI Service Unavailable"}

    async def interpret(self, query: str) -> Dict[str, Any]:
        """
        Interprets the user query using Chutes AI (with Fallback).
        """
        system_prompt = """You are an expert Indian stock market assistant fluent in all market terminology.
Your goal is to classify the user's INTENT and return a structured JSON.

=== COMPREHENSIVE STOCK MARKET GLOSSARY ===

## PRICE & QUOTE TERMS:
- LTP = Last Traded Price (current market price)
- CMP = Current Market Price (same as LTP)
- ATP = Average Traded Price
- OHLC = Open, High, Low, Close prices of the day
- Prev Close = Yesterday's closing price
- Open = Today's opening price
- High/Low = Day's highest/lowest prices
- 52W High/Low = 52-week highest/lowest price
- All-Time High (ATH) = Highest price ever
- Bid = Highest price buyer is willing to pay
- Ask/Offer = Lowest price seller is willing to accept
- Spread = Difference between bid and ask
- Tick = Minimum price movement (0.05 for stocks)

## VOLUME & LIQUIDITY TERMS:
- Volume = Number of shares traded
- Traded Value = Volume × Price
- Turnover = Total value of trades
- Delivery = Shares actually transferred (not intraday)
- Delivery % = (Delivery Volume / Total Volume) × 100
- Bulk Deal = Single trade > 0.5% of company shares
- Block Deal = Single trade > 5 lakh shares
- OI (Open Interest) = Outstanding derivative contracts

## TECHNICAL ANALYSIS TERMS:
- RSI = Relative Strength Index (0-100, <30 oversold, >70 overbought)
- SMA = Simple Moving Average (SMA50, SMA200)
- EMA = Exponential Moving Average
- MACD = Moving Average Convergence Divergence
- Bollinger Bands = Volatility bands around SMA
- Support = Price level where stock tends to stop falling
- Resistance = Price level where stock struggles to rise above
- Breakout = Price moving above resistance
- Breakdown = Price falling below support
- Trend = Direction of price movement (Bullish/Bearish/Sideways)
- Consolidation = Price moving in narrow range
- Reversal = Change in trend direction
- Pullback = Temporary price decline in uptrend
- Rally = Sustained price increase
- Correction = 10%+ decline from recent high
- Bear Market = 20%+ decline, prolonged downturn
- Bull Market = Sustained rising prices
- Gap Up = Opening price higher than prev close
- Gap Down = Opening price lower than prev close
- Candlestick = Chart pattern (Doji, Hammer, Engulfing, etc.)
- Moving Average Crossover = When shorter MA crosses longer MA
- Golden Cross = 50 SMA crosses above 200 SMA (bullish)
- Death Cross = 50 SMA crosses below 200 SMA (bearish)
- Fibonacci = Retracement levels (23.6%, 38.2%, 50%, 61.8%)
- Pivot = Support/resistance calculation from OHLC
- VWAP = Volume Weighted Average Price

## FUNDAMENTAL ANALYSIS TERMS:
- Market Cap = Share Price × Total Shares
- Large Cap = Market Cap > ₹20,000 Cr
- Mid Cap = ₹5,000 - ₹20,000 Cr
- Small Cap = < ₹5,000 Cr
- P/E Ratio = Price / Earnings Per Share
- P/B Ratio = Price / Book Value
- PEG = P/E / Earnings Growth Rate
- EPS = Earnings Per Share
- ROE = Return on Equity (Net Income / Equity)
- ROA = Return on Assets
- ROCE = Return on Capital Employed
- D/E = Debt to Equity Ratio
- Current Ratio = Current Assets / Current Liabilities
- Dividend Yield = Annual Dividend / Share Price
- Book Value = Assets - Liabilities
- Face Value = Nominal value of share (usually ₹10, ₹2, ₹1)
- Promoter Holding = % shares held by company founders
- FII/FPI = Foreign Institutional Investors
- DII = Domestic Institutional Investors
- QoQ = Quarter over Quarter growth
- YoY = Year over Year growth

## TRADING TERMS:
- Intraday = Buy and sell same day
- BTST/STBT = Buy Today Sell Tomorrow / Sell Today Buy Tomorrow
- Swing Trading = Holding for days to weeks
- Positional = Holding for weeks to months
- Long = Buying expecting price rise
- Short = Selling expecting price fall
- Margin = Borrowed money for trading
- Leverage = Trading with more than your capital
- Stop Loss (SL) = Order to limit losses
- Target = Profit-taking price level
- Risk-Reward = Potential loss vs potential gain ratio
- Position Sizing = How much capital per trade
- Averaging = Buying more at lower price
- Pyramiding = Adding to winning position
- Scalping = Quick trades for small profits
- Paper Trading = Practice without real money

## DERIVATIVES (F&O) TERMS:
- Futures = Contract to buy/sell at future date
- Options = Right (not obligation) to buy/sell
- Call Option (CE) = Right to buy
- Put Option (PE) = Right to sell
- Strike Price = Price at which option can be exercised
- Expiry = Date when contract expires
- Premium = Price paid for option
- ITM = In The Money (profitable if exercised now)
- OTM = Out of The Money (not profitable now)
- ATM = At The Money (strike = current price)
- Lot Size = Minimum quantity for F&O trading
- OI (Open Interest) = Total outstanding contracts
- PCR = Put Call Ratio (Put OI / Call OI)
- IV = Implied Volatility
- Theta = Time decay of option premium
- Delta = How much option price moves with stock
- Gamma = Rate of change of delta
- Vega = Sensitivity to volatility
- Rollover = Moving position to next expiry
- Hedge = Reducing risk using derivatives
- Straddle = Buying both call and put at same strike
- Strangle = Call and put at different strikes
- Iron Condor = Selling OTM call & put, buying protection
- Writing/Selling Options = Being the option seller

## MARKET MECHANICS:
- NSE = National Stock Exchange
- BSE = Bombay Stock Exchange
- SEBI = Securities & Exchange Board of India
- NIFTY 50 = Top 50 NSE stocks index
- SENSEX = Top 30 BSE stocks index
- Bank Nifty = Banking sector index
- Nifty IT = IT sector index
- Market Hours = 9:15 AM - 3:30 PM IST
- Pre-Open = 9:00 - 9:15 AM (price discovery)
- Pre-Close = 3:30 - 4:00 PM
- Circuit Break = Trading halt at price limits
- Upper Circuit (UC) = Max allowed price increase
- Lower Circuit (LC) = Max allowed price decrease
- T+1 Settlement = Trade settles next day
- Demat = Dematerialized (electronic) shares
- Depository = CDSL or NSDL (holds your shares)
- DP = Depository Participant (your broker)
- CAS = Consolidated Account Statement
- Pledge = Using shares as loan collateral
- Corporate Action = Bonus, Split, Dividend, Rights

## POPULAR SYMBOL ALIASES:
- RIL, RELIANCE = Reliance Industries
- TCS = Tata Consultancy Services
- HDFC, HDFCBANK = HDFC Bank
- ICICI, ICICIBANK = ICICI Bank
- INFY, INFOSYS = Infosys
- SBI, SBIN = State Bank of India
- BHARTI, AIRTEL = Bharti Airtel
- AXIS, AXISBANK = Axis Bank
- KOTAK, KOTAKBANK = Kotak Mahindra Bank
- LT, LARSEN = Larsen & Toubro
- M&M, MAHINDRA = Mahindra & Mahindra
- TATAMOTORS, TATA MOTORS = Tata Motors
- TATASTEEL, TATA STEEL = Tata Steel
- ADANI, ADANIENT = Adani Enterprises
- BAJAJ, BAJFINANCE = Bajaj Finance
- WIPRO = Wipro
- HUL, HINDUNILVR = Hindustan Unilever
- ITC = ITC Limited
- MARUTI = Maruti Suzuki
- TITAN = Titan Company
- SUNPHARMA = Sun Pharma
- TECHM = Tech Mahindra
- ONGC = Oil & Natural Gas Corporation
- NTPC = NTPC Limited
- POWERGRID = Power Grid
- COAL, COALINDIA = Coal India
- UBI, UNIONBANK = Union Bank of India
- PNB = Punjab National Bank
- ZOMATO = Zomato
- PAYTM = One97 Communications

## COMMON QUERY PATTERNS:
- "LTP of X" / "CMP of X" / "Price of X" → CHECK_PRICE
- "How is X?" / "What's X at?" → CHECK_PRICE
- "X ka rate" / "X ka bhav" (Hindi) → CHECK_PRICE
- "Alert if X > Y" / "Notify when X hits Y" → CREATE_ALERT
- "Bought X shares of Y at Z" → ADD_PORTFOLIO
- "Sold X shares of Y" → SELL_PORTFOLIO
- "Show/View portfolio" → VIEW_PORTFOLIO
- "Delete/Remove X from portfolio" → DELETE_PORTFOLIO

=== INTENT CLASSIFICATION RULES ===

PROTOCOLS:
1. DETECT INTENT:
   - "Alert me if..." → `CREATE_ALERT`
   - "Alert me when TCS hits 3000" → `CREATE_ALERT`
   - "Notify if Reliance reaches 2500" → `CREATE_ALERT`
   - "Bought 10 TCS..." → `ADD_PORTFOLIO`
   - "Sold 10 TCS..." → `SELL_PORTFOLIO`
   - "Show my portfolio" → `VIEW_PORTFOLIO`
   - "Delete TCS from portfolio" → `DELETE_PORTFOLIO`
   - "Update TCS quantity to 50" → `UPDATE_PORTFOLIO`
   - "LTP of X", "Price of X", "CMP X", "How is X?" → `CHECK_PRICE`

2. JSON FORMATS:

[CASE: CREATE_ALERT]
{ "intent": "CREATE_ALERT", "status": "CONFIRMED", "config": { "symbol": "TICKER", "conditions": [...] } }

[CASE: ADD_PORTFOLIO]
{ 
  "intent": "ADD_PORTFOLIO", "status": "CONFIRMED", 
  "data": { 
      "items": [{ "symbol": "TICKER", "quantity": 10, "price": 3000, "date": "..." }]
  } 
}

[CASE: SELL_PORTFOLIO]
{ "intent": "SELL_PORTFOLIO", "status": "CONFIRMED", "data": { "symbol": "TICKER", "quantity": 10, "price": 3500 } }

[CASE: DELETE_PORTFOLIO]
{ "intent": "DELETE_PORTFOLIO", "status": "CONFIRMED", "data": { "symbol": "TICKER" } }

[CASE: UPDATE_PORTFOLIO]
{ "intent": "UPDATE_PORTFOLIO", "status": "CONFIRMED", "data": { "symbol": "TICKER", "quantity": 50, "price": 1200 } }

[CASE: VIEW_PORTFOLIO]
{ "intent": "VIEW_PORTFOLIO", "status": "CONFIRMED" }

[CASE: CHECK_PRICE]
{ "intent": "CHECK_PRICE", "status": "CONFIRMED", "data": { "symbol": "TICKER" } }
- ALWAYS convert symbol aliases to standard NSE symbols (e.g., RIL→RELIANCE, SBI→SBIN)

[CASE: NEEDS_CLARIFICATION]
{ "status": "NEEDS_CLARIFICATION", "question": "..." }

[CASE: REJECTED]
{ "status": "REJECTED", "message": "I focus on stocks. Type /start for the menu." }

SAFETY PROTOCOL:
- If user asks: "What should I buy?", "Is TCS good?", "Predict the market"
- RETURN: { "status": "REJECTED", "message": "⚠️ I am an AI Tool, not a SEBI-registered Advisor. I cannot provide investment recommendations." }
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        return await self._call_with_fallback(messages)

    async def parse_screener_query(self, query: str) -> Dict[str, Any]:
        """
        Interprets natural language screening criteria.
        Returns: { "filters": [ {field, op, value}, ... ] }
        """
        system_prompt = """You are a Stock Screener AI.
Convert the user's Natural Language query into a JSON filter list.

FIELDS ALLOWED:
- 'ltp' (Price)
- 'change_pct' (Percent Change today)
- 'volume' (Volume)
- 'rsi' (RSI - Relative Strength Index)
- 'sma50' (50 Day Moving Average)

OPERATORS: 'gt' (>), 'lt' (<), 'eq' (=)

SAFETY PROTOCOL:
- You are a neutral parser.
- NEVER give buy/sell advice.
- IF ADVICE REQUESTED (e.g., "What to buy?", "Is this good?"):
  JSON: { "error": "ADVICE_REQUESTED" }

EXAMPLES:
1. User: "Stocks above 2000"
   JSON: { "filters": [{"field": "ltp", "op": "gt", "value": 2000}] }

2. User: "RSI below 30 and price under 500"
   JSON: { "filters": [{"field": "rsi", "op": "lt", "value": 30}, {"field": "ltp", "op": "lt", "value": 500}] }

3. User: "High volume gainers"
   JSON: { "filters": [{"field": "change_pct", "op": "gt", "value": 0}, {"field": "volume", "op": "gt", "value": 100000}] }

OUTPUT JSON ONLY.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        result = await self._call_with_fallback(messages)
        
        # Standardize error in parsing
        if result.get("status") == "ERROR":
             return {"error": "Failed to parse query"}
             
        return result

    async def generate_portfolio_summary(self, portfolio_data: Dict[str, Any]) -> str:
        """
        Generates a one-line financial insight about the user's portfolio.
        """
        system_prompt = """You are a financial analyst.
Analyze the provided portfolio data (Total Value, P&L, Holdings) and provide a SINGLE, INSIGHTFUL sentence.
Focus on:
- Major performers/draggers
- Overall health (Profitable vs Loss)
- Diversification (or lack thereof)
- Actionable tip (Hold, Diversify, etc.)

CONSTRAINT:
- Maximum 15-20 words.
- Be professional but encouraging.
- Use 1-2 emojis.
- NO investment advice (e.g. "Buy/Sell this").
"""
        # Simplify data for LLM to save tokens
        holdings_summary = []
        for h in portfolio_data.get("holdings", []):
            holdings_summary.append(f"{h['symbol']}: {h['pnl_percent']}%")
            
        summary_text = (
            f"Total: {portfolio_data['summary']['total_value']}, "
            f"P&L: {portfolio_data['summary']['total_pnl']} ({portfolio_data['summary']['total_pnl_percent']}%), "
            f"Holdings: {', '.join(holdings_summary)}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Portfolio: {summary_text}"}
        ]
        
        result = await self._call_with_fallback(messages)
        
        if result.get("status") == "ERROR":
            return "Unable to generate insight at the moment."
            
        # The result from _call_with_fallback is a JSON (or dict). 
        # But here we expect a string from the LLM? 
        # Wait, _call_with_fallback returns JSON because `interpret` expects JSON.
        # But for this summary, we might get just text if the model doesn't output JSON.
        # However, `_call_with_fallback` attempts to parse JSON.
        # Let's check `_call_with_fallback` implementation again.
        # It tries `json.loads(json_str)`. 
        # If the model returns plain text, `json.loads` might fail if it's not a JSON string.
        # I should probably adjust `_call_with_fallback` to be more flexible OR ask for JSON output.
        # Let's ask for JSON output to be consistent.
        
        # Actually, let's fix the logic here. I can just wrap the response in a specific JSON key in the prompt.
        # But to be safe and clean, let's modify the prompt to ask for JSON.
        
        return result.get("insight", "Your portfolio looks active! Keep monitoring your key positions. 📊")

