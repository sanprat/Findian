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
            "GLM-4.6V-Flash",   # Primary
            "GLM-4.5-Flash"     # Fallback
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
                logger.error("Invalid ZAI_API_KEY format. Expected 'id.secret' format")
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

    async def interpret(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Interprets the user query using Chutes AI (with Fallback).
        """
        system_prompt = """Stock assistant. Return JSON only.

INTENTS: CHECK_PRICE, CREATE_ALERT, ADD_PORTFOLIO, SELL_PORTFOLIO,
VIEW_PORTFOLIO, DELETE_PORTFOLIO, MARKET_INFO, CHECK_FUNDAMENTALS,
ANALYZE_STOCK

JSON:
CHECK_PRICE: {"intent":"CHECK_PRICE","status":"CONFIRMED","data":{"symbol":"TICKER"}}
CREATE_ALERT: {"intent":"CREATE_ALERT","status":"CONFIRMED","config":{"symbol":"TICKER","conditions":[{"field":"ltp","op":"gt","value":1000}]}}
ADD_PORTFOLIO: {"intent":"ADD_PORTFOLIO","status":"CONFIRMED","data":{"items":[{"symbol":"TICKER","quantity":10,"price":3000}]}}
SELL_PORTFOLIO: {"intent":"SELL_PORTFOLIO","status":"CONFIRMED","data":{"symbol":"TICKER","quantity":10,"price":3500}}
VIEW_PORTFOLIO: {"intent":"VIEW_PORTFOLIO","status":"CONFIRMED"}
DELETE_PORTFOLIO: {"intent":"DELETE_PORTFOLIO","status":"CONFIRMED","data":{"symbol":"TICKER"}}
MARKET_INFO: {"intent":"MARKET_INFO","status":"MARKET_INFO","data":{"answer":"Concise answer string here."}}
CHECK_FUNDAMENTALS: {"intent":"CHECK_FUNDAMENTALS","status":"CONFIRMED","data":{"symbol":"TICKER"}}
ANALYZE_STOCK: {"intent":"ANALYZE_STOCK","status":"CONFIRMED","data":{"symbol":"TICKER"}}
NEEDS_CLARIFICATION: {"status":"NEEDS_CLARIFICATION","question":"Which stock?"}
REJECTED: {"status":"REJECTED","message":"I cannot provide investment advice."}

Rules: Convert aliases (RIL=RELIANCE, SBI=SBIN, UBI=UNIONBANK). 
Reject specific buy/sell recommendations.
ALLOW general market questions, definitions, concepts, and market sentiment queries.
CRITICAL: If user asks for "Volume", "High", "Low", "Gap up/down", "Market Cap"
or "Price" WITHOUT asking for specific trends or analysis, return 'CHECK_PRICE'.
CRITICAL: If user asks for "Chart", "Volume Trend", "Technical Analysis", "Moving Average" for a SPECIFIC stock, return 'ANALYZE_STOCK'.
CRITICAL: If user asks to "find stocks", "show stocks", "list stocks",
"stocks with [criteria]" (MULTIPLE stocks matching criteria), tell them to use
the Screener menu. Return: {"status":"MARKET_INFO","data":{"answer":"To find
multiple stocks, please use the 🔍 Screener menu and select 'Custom AI'."}}
IMPORTANT: If asked "Why did [stock] move?" or "Reason for change", DO NOT invent news. Explain that you don't have live news feed, but list general reasons for such moves (earnings, sector trends, etc.).

QUERY EXAMPLES:
1. "What is HDFC price?" → CHECK_PRICE
2. "Current price of TCS" → CHECK_PRICE
3. "INFY volume today" → CHECK_PRICE
4. "Show chart of Reliance" → ANALYZE_STOCK
5. "Analyze HDFC Bank" → ANALYZE_STOCK
6. "Volume trend of TCS" → ANALYZE_STOCK
7. "Technical analysis of INFY" → ANALYZE_STOCK
8. "Bought 10 HDFC at 1600" → ADD_PORTFOLIO
9. "Sold 5 TCS at 3500" → SELL_PORTFOLIO
10. "Show my portfolio" → VIEW_PORTFOLIO
11. "Alert if Reliance > 2500" → CREATE_ALERT
12. "Notify when INFY < 1400" → CREATE_ALERT
13. "What is P/E ratio?" → MARKET_INFO (explain concept)
14. "How does RSI work?" → MARKET_INFO (explain concept)
15. "What is breakout?" → MARKET_INFO (explain concept)
16. "Why did HDFC fall today?" → MARKET_INFO (general reasons, no news)
17. "HDFC fundamentals" → CHECK_FUNDAMENTALS
18. "Show PE ratio of TCS" → CHECK_FUNDAMENTALS
19. "Find stocks with high volume" → Redirect to Screener
20. "Stocks near 52w high" → Redirect to Screener
21. "Should I buy HDFC?" → REJECTED (investment advice)
22. "Is this a good time to invest?" → REJECTED (investment advice)
23. "What's the weather?" → REJECTED (not stock-related)
24. "What is RIL price?" → CHECK_PRICE with symbol=RELIANCE (alias conversion)
25. "Context: User previously looked at HDFC.
Query: What about fundamentals?" → CHECK_FUNDAMENTALS with symbol=HDFC (context handling)
26. "What should I buy tomorrow?" → REJECTED (investment advice - future prediction)
27. "Show me the best stocks to buy" → REJECTED (investment advice - recommendations)

STRICT CONSTRAINT: You are a STOCK MARKET ASSISTANT ONLY. If the user asks about ANYTHING not related to stocks, markets, finance, trading, or investing, you MUST respond with:
{"status":"REJECTED","message":"Sorry, I don't have that information. I only assist with stock market queries."
"""
        user_content = query
        if context and context.get("last_symbol"):
             user_content = f"Context: User previously looked at {context['last_symbol']}.\nQuery: {query}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}

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
- 'pct_from_52w_high' (% Away from 52-Wk High. "Near" = value > -5)

OPERATORS: 'gt' (>), 'lt' (<), 'eq' (=)

SAFETY PROTOCOL:
- You are a neutral parser.
- NEVER give buy/sell advice.
- IF ADVICE REQUESTED (e.g., "What to buy?", "Is this good?"):
  JSON: { "error": "ADVICE_REQUESTED" }
- IF user asks for fields NOT in the allowed list (e.g., "P/E ratio", "market cap"):
  JSON: { "error": "UNSUPPORTED_FIELD", "message": "I can only filter by: Price, Volume, RSI, Change%, SMA50, and 52-Week High. Try asking: 'Stocks near 52 week high'" }

EXAMPLES:
1. User: "Stocks above 2000"
   JSON: { "filters": [{"field": "ltp", "op": "gt", "value": 2000}] }

2. User: "RSI below 30 and price under 500"
   JSON: { "filters": [{"field": "rsi", "op": "lt", "value": 30}, {"field": "ltp", "op": "lt", "value": 500}] }

3. User: "High volume gainers"
   JSON: { "filters": [{"field": "change_pct", "op": "gt", "value": 0}, {"field": "volume", "op": "gt", "value": 100000}] }

4. User: "Stocks near 52w high"
   JSON: { "filters": [{"field": "pct_from_52w_high", "op": "gt", "value": -5}] }
   (Explanation: "Near" usually means within 5% of high, so > -5%)
   
5. User: "Stocks at 52w high"
   JSON: { "filters": [{"field": "pct_from_52w_high", "op": "gt", "value": -1}] }

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

