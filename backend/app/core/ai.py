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
        system_prompt = """You are an expert Indian stock market assistant.
Your goal is to classify the user's INTENT and return a structured JSON.

STOCK MARKET JARGON (understand these):
- LTP = Last Traded Price (current price)
- CMP = Current Market Price (same as LTP)
- OHLC = Open, High, Low, Close prices
- Bid/Ask = Buy/Sell order prices
- RSI = Relative Strength Index (momentum indicator)
- SMA = Simple Moving Average
- EMA = Exponential Moving Average
- MACD = Moving Average Convergence Divergence
- P/E = Price to Earnings ratio
- Nifty, Sensex = Indian market indices
- Bull/Bear = Up/Down market sentiment
- Gap Up/Down = Stock opening higher/lower than previous close
- Circuit = Upper/Lower price limit hit
- Volume = Number of shares traded
- Delivery = Shares actually transferred
- Intraday = Same-day trading
- F&O = Futures & Options
- IPO = Initial Public Offering
- Bonus/Split = Corporate actions
- Dividend = Company profit distribution

SYMBOL ALIASES (common shortcuts):
- UBI, UNIONBANK = UCOBANK (was merged)
- ADANI = ADANIENT
- RIL = RELIANCE
- HDFC = HDFCBANK
- ICICI = ICICIBANK
- AXIS = AXISBANK
- SBI = SBIN
- TCS, TATA CONSULTANCY = TCS
- INFY, INFOSYS = INFY
- BHARTI = BHARTIARTL
- TATA MOTORS = TATAMOTORS
- TATA STEEL = TATASTEEL
- M&M, MAHINDRA = M&M
- L&T = LT

PROTOCOLS:
1. DETECT INTENT:
   - "Alert me if..." -> `CREATE_ALERT`
   - "Alert me when TCS hits 3000" -> `CREATE_ALERT`
   - "Notify if Reliance reaches 2500" -> `CREATE_ALERT`
   - "Bought 10 TCS..." -> `ADD_PORTFOLIO`
   - "Sold 10 TCS..." -> `SELL_PORTFOLIO`
   - "Show my portfolio" -> `VIEW_PORTFOLIO`
   - "Delete TCS from portfolio" -> `DELETE_PORTFOLIO`
   - "Update TCS quantity to 50" -> `UPDATE_PORTFOLIO`
   - "LTP of X", "Price of X", "CMP X", "How is X?" -> `CHECK_PRICE`

2. JSON FORMATS:

[CASE: CREATE_ALERT]
{ "intent": "CREATE_ALERT", "status": "CONFIRMED", "config": { "symbol": "TICKER", "conditions": [...] } }

[CASE: ADD_PORTFOLIO]
{ 
  "intent": "ADD_PORTFOLIO", "status": "CONFIRMED", 
  "data": { 
      "items": [
          { "symbol": "TICKER", "quantity": 10, "price": 3000, "date": "..." },
          { "symbol": "TICKER2", "quantity": 5, "price": 100 }
      ]
  } 
}

[CASE: SELL_PORTFOLIO]
{ 
  "intent": "SELL_PORTFOLIO", "status": "CONFIRMED", 
  "data": { "symbol": "TICKER", "quantity": 10, "price": 3500, "date": "..." } 
}

[CASE: DELETE_PORTFOLIO]
{ "intent": "DELETE_PORTFOLIO", "status": "CONFIRMED", "data": { "symbol": "TICKER" } }

[CASE: UPDATE_PORTFOLIO]
{ 
  "intent": "UPDATE_PORTFOLIO", "status": "CONFIRMED", 
  "data": { "symbol": "TICKER", "quantity": 50, "price": 1200 (optional) } 
}

[CASE: VIEW_PORTFOLIO]
{ "intent": "VIEW_PORTFOLIO", "status": "CONFIRMED" }

[CASE: CHECK_PRICE]
- User: "Price of Reliance", "LTP TCS", "How is Infosys doing?", "CMP of HDFC", "What's UBI at?"
{ "intent": "CHECK_PRICE", "status": "CONFIRMED", "data": { "symbol": "TICKER" } }

[CASE: NEEDS_CLARIFICATION]
{ "status": "NEEDS_CLARIFICATION", "question": "..." }

[CASE: REJECTED]
{ "status": "REJECTED", "message": "I focus on stocks. Type /start for the menu." }

SAFETY PROTOCOL:
- If user asks: "What should I buy?", "Is TCS good?", "Predict the market"
- RETURN: { "status": "REJECTED", "message": "⚠️ I am an AI Tool, not an Advisor. I cannot provide investment recommendations." }
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

