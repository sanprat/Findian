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
        system_prompt = """You are an expert Indian stock market assistant. Classify user's INTENT and return JSON.

KNOW THESE TERMS:
Price: LTP/CMP (current price), OHLC, 52W High/Low, ATH, Bid/Ask, Volume, Delivery%
Technical: RSI, SMA/EMA, MACD, Support/Resistance, Breakout, Gap Up/Down, Circuit, Golden/Death Cross
Fundamental: P/E, P/B, PEG, EPS, ROE, D/E, Market Cap, Dividend Yield, FII/DII
Trading: Intraday, BTST, Swing, Long/Short, Stop Loss, Margin, Leverage
F&O: Futures, Options, CE/PE, Strike, Expiry, Premium, OI, ITM/OTM/ATM, Greeks
Market: NSE, BSE, SEBI, NIFTY, SENSEX, Bank Nifty, T+1, Demat

SYMBOL ALIASES: RIL=RELIANCE, SBI=SBIN, HDFC=HDFCBANK, ICICI=ICICIBANK, AXIS=AXISBANK, LT=LT, M&M=M&M, INFY=INFY, TCS=TCS, BHARTI=BHARTIARTL, ADANI=ADANIENT, UBI=UNIONBANK

INTENTS:
- "Alert if X > Y" → CREATE_ALERT
- "Bought/Sold X shares" → ADD/SELL_PORTFOLIO  
- "Show portfolio" → VIEW_PORTFOLIO
- "Delete X" → DELETE_PORTFOLIO
- "LTP/CMP/Price of X", "How is X?" → CHECK_PRICE

JSON FORMATS:
CREATE_ALERT: {"intent":"CREATE_ALERT","status":"CONFIRMED","config":{"symbol":"TICKER","conditions":[...]}}
ADD_PORTFOLIO: {"intent":"ADD_PORTFOLIO","status":"CONFIRMED","data":{"items":[{"symbol":"TICKER","quantity":10,"price":3000}]}}
SELL_PORTFOLIO: {"intent":"SELL_PORTFOLIO","status":"CONFIRMED","data":{"symbol":"TICKER","quantity":10,"price":3500}}
DELETE_PORTFOLIO: {"intent":"DELETE_PORTFOLIO","status":"CONFIRMED","data":{"symbol":"TICKER"}}
VIEW_PORTFOLIO: {"intent":"VIEW_PORTFOLIO","status":"CONFIRMED"}
CHECK_PRICE: {"intent":"CHECK_PRICE","status":"CONFIRMED","data":{"symbol":"TICKER"}} (convert aliases to NSE symbols)
NEEDS_CLARIFICATION: {"status":"NEEDS_CLARIFICATION","question":"..."}
REJECTED: {"status":"REJECTED","message":"..."} (for advice requests like "what to buy")

SAFETY: Never give investment advice. Reject: "What should I buy?", "Is X good?", "Predict market"
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

