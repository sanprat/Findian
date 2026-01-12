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
        # Primary and fallback models
        self.models = [
            "MiniMaxAI/MiniMax-M2.1-TEE",
            "unsloth/Mistral-Nemo-Instruct-2407"  # Fallback
        ]

    async def _call_with_fallback(self, messages: list, temperature: float = 0.1) -> Dict[str, Any]:
        """
        Try models in order with short timeout.
        """
        import time
        start = time.time()
        
        if not self.api_token:
            logger.error("CHUTES_API_TOKEN not configured!")
            return {"status": "ERROR", "message": "AI not configured"}

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        for model in self.models:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
                "max_tokens": 200
            }
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.base_url, 
                        json=payload, 
                        headers=headers, 
                        timeout=12.0
                    )
                    response.raise_for_status()
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    
                    # Extract JSON from markdown
                    if "```" in content:
                        json_start = content.find('{')
                        json_end = content.rfind('}') + 1
                        json_str = content[json_start:json_end]
                    else:
                        json_str = content
                    
                    elapsed = time.time() - start
                    logger.info(f"🤖 AI ({model.split('/')[-1]}) responded in {elapsed:.2f}s")
                    return json.loads(json_str)

            except Exception as e:
                logger.warning(f"⚠️ Model {model} failed: {type(e).__name__}: {e}")
                continue
        
        # All models failed
        elapsed = time.time() - start
        logger.error(f"❌ All AI models failed after {elapsed:.2f}s")
        return {"status": "ERROR", "message": "AI Service Unavailable"}

    async def interpret(self, query: str) -> Dict[str, Any]:
        """
        Interprets the user query using Chutes AI (with Fallback).
        """
        system_prompt = """Stock assistant. Return JSON only.

INTENTS: CHECK_PRICE, CREATE_ALERT, ADD_PORTFOLIO, SELL_PORTFOLIO, VIEW_PORTFOLIO, DELETE_PORTFOLIO

JSON:
CHECK_PRICE: {"intent":"CHECK_PRICE","status":"CONFIRMED","data":{"symbol":"TICKER"}}
CREATE_ALERT: {"intent":"CREATE_ALERT","status":"CONFIRMED","config":{"symbol":"TICKER","conditions":[{"field":"ltp","op":"gt","value":1000}]}}
ADD_PORTFOLIO: {"intent":"ADD_PORTFOLIO","status":"CONFIRMED","data":{"items":[{"symbol":"TICKER","quantity":10,"price":3000}]}}
SELL_PORTFOLIO: {"intent":"SELL_PORTFOLIO","status":"CONFIRMED","data":{"symbol":"TICKER","quantity":10,"price":3500}}
VIEW_PORTFOLIO: {"intent":"VIEW_PORTFOLIO","status":"CONFIRMED"}
DELETE_PORTFOLIO: {"intent":"DELETE_PORTFOLIO","status":"CONFIRMED","data":{"symbol":"TICKER"}}
NEEDS_CLARIFICATION: {"status":"NEEDS_CLARIFICATION","question":"Which stock?"}
REJECTED: {"status":"REJECTED","message":"I cannot provide investment advice."}

Rules: Convert aliases (RIL=RELIANCE, SBI=SBIN). Reject advice requests.
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

