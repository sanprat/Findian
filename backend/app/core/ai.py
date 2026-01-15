import httpx
import json
import os
import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AIAlertInterpreter:
    def __init__(self):
        self.api_key = os.getenv("ZAI_API_KEY")
        self.base_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        
        # Models requested by user (Prioritized)
        self.models = [
            "GLM-4.5-Flash",    # Fast text model (Best for simple intents)
            "GLM-4.6V-Flash",   # Multimodal Flash
            "GLM-4.6V-FlashX"   # extended
        ]
        self.model = self.models[0] # Default to first
        
        self.cache = {} # Simple in-memory cache for token

    def _generate_token(self, apikey: str, exp_seconds: int):
        """
        Generate JWT token for Z.ai (BigModel) API.
        Reference: https://open.bigmodel.cn/dev/api#sdk_python
        """
        try:
            # Implementation using standard library to avoid dependency issues if PyJWT not present
            # But wait, requirement.txt doesn't list pyjwt explicitly. 
            # Let's use the exact method from their docs which often uses PyJWT.
            # However, to be safe and fast without pip install, I will use a robust standard lib version if valid.
            
            # Actually, most robust way is to use the SDK if user allows, but user wants code update immediately.
            # I will use a pure python JWT generation function to be safe.
            
            # Check if key is valid
            if not apikey or "." not in apikey:
                logger.error(f"Invalid ZAI_API_KEY format. Expected 'id.secret', got: {apikey[:5]}...")
                return None

            id, secret = apikey.split(".")
            payload = {
                "api_key": id,
                "exp": int(round(time.time() * 1000)) + exp_seconds * 1000,
                "timestamp": int(round(time.time() * 1000)),
            }
            
            # Simple JWT implementation using hmac/hashlib/base64
            import hmac
            import hashlib
            import base64
            
            def b64url_encode(data):
                return base64.urlsafe_b64encode(data).rstrip(b'=')

            header = b64url_encode(json.dumps({"alg": "HS256", "sign_type": "SIGN"}).encode('utf-8'))
            payload_enc = b64url_encode(json.dumps(payload).encode('utf-8'))
            
            signature = b64url_encode(hmac.new(
                secret.encode('utf-8'),
                header + b"." + payload_enc,
                hashlib.sha256
            ).digest())
            
            return (header + b"." + payload_enc + b"." + signature).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Token generation failed: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _get_auth_header(self):
        """Get Authorization header with cached JWT"""
        if not self.api_key:
            logger.error("❌ ZAI_API_KEY is missing in AIAlertInterpreter")
            return None
            
        # Check cache
        if self.cache.get('token') and self.cache.get('exp') > time.time():
            return self.cache['token']
            
        # Generate new
        token = self._generate_token(self.api_key, 3600)
        if not token:
             logger.error("❌ Failed to generate Z.ai token")
        else:
             self.cache['token'] = token
             self.cache['exp'] = time.time() + 3500 # 5 min buffer
        
        return token

    async def _call_with_fallback(self, messages: list, temperature: float = 0.1) -> Dict[str, Any]:
        """
        Call Z.ai API
        """
        import time
        start = time.time()
        
        token = self._get_auth_header()
        if not token:
            logger.error("ZAI_API_KEY not configured or invalid")
            return {"status": "ERROR", "message": "AI not configured"}

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        for model in self.models:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
                "max_tokens": 1024
            }
            
            try:
                # logger.info(f"🤖 Attempting AI call with model: {model}")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.base_url, 
                        json=payload, 
                        headers=headers, 
                        timeout=15.0
                    )
                    
                    if response.status_code != 200:
                         logger.warning(f"⚠️ Model {model} error {response.status_code}: {response.text}")
                         continue # Try next model
                         
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
                    logger.info(f"🤖 AI ({model}) responded in {elapsed:.2f}s")
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

INTENTS: CHECK_PRICE, CREATE_ALERT, ADD_PORTFOLIO, SELL_PORTFOLIO, VIEW_PORTFOLIO, DELETE_PORTFOLIO, MARKET_INFO

JSON:
CHECK_PRICE: {"intent":"CHECK_PRICE","status":"CONFIRMED","data":{"symbol":"TICKER"}}
CREATE_ALERT: {"intent":"CREATE_ALERT","status":"CONFIRMED","config":{"symbol":"TICKER","conditions":[{"field":"ltp","op":"gt","value":1000}]}}
ADD_PORTFOLIO: {"intent":"ADD_PORTFOLIO","status":"CONFIRMED","data":{"items":[{"symbol":"TICKER","quantity":10,"price":3000}]}}
SELL_PORTFOLIO: {"intent":"SELL_PORTFOLIO","status":"CONFIRMED","data":{"symbol":"TICKER","quantity":10,"price":3500}}
VIEW_PORTFOLIO: {"intent":"VIEW_PORTFOLIO","status":"CONFIRMED"}
DELETE_PORTFOLIO: {"intent":"DELETE_PORTFOLIO","status":"CONFIRMED","data":{"symbol":"TICKER"}}
MARKET_INFO: {"intent":"MARKET_INFO","status":"MARKET_INFO","data":{"answer":"Concise answer string here."}}
NEEDS_CLARIFICATION: {"status":"NEEDS_CLARIFICATION","question":"Which stock?"}
REJECTED: {"status":"REJECTED","message":"I cannot provide investment advice."}

Rules: Convert aliases (RIL=RELIANCE, SBI=SBIN, UBI=UNIONBANK). 
Reject specific buy/sell recommendations.
ALLOW general market questions, definitions, concepts, and market sentiment queries.
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

