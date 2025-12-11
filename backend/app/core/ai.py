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
        self.model = "openai/gpt-oss-20b"

    async def interpret(self, query: str) -> Dict[str, Any]:
        """
        Interprets the user query using Chutes AI.
        """
        if not self.api_token:
            return {
                "status": "ERROR",
                "message": "CHUTES_API_TOKEN not configured"
            }

        system_prompt = """You are an expert stock assistant.
Your goal is to classify the user's INTENT and return a structured JSON.

PROTOCOLS:
1. DETECT INTENT:
   - "Alert me if..." -> `CREATE_ALERT`
   - "Bought 10 TCS..." -> `ADD_PORTFOLIO`
   - "Show my portfolio" -> `VIEW_PORTFOLIO`
   - "Delete TCS from portfolio" -> `DELETE_PORTFOLIO`
   - "Update TCS quantity to 50" -> `UPDATE_PORTFOLIO`

2. JSON FORMATS:

[CASE: CREATE_ALERT]
{ "intent": "CREATE_ALERT", "status": "CONFIRMED", "config": { "symbol": "TICKER", "conditions": [...] } }

[CASE: ADD_PORTFOLIO]
{ 
  "intent": "ADD_PORTFOLIO", "status": "CONFIRMED", 
  "data": { "symbol": "TICKER", "quantity": 10, "price": 3000, "date": "..." } 
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

[CASE: NEEDS_CLARIFICATION]
{ "status": "NEEDS_CLARIFICATION", "question": "..." }

[CASE: REJECTED]
{ "status": "REJECTED", "message": "..." }
"""
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "temperature": 0.1, # Low temperature for consistent JSON
            "stream": False
        }

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        try:
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
                
                # Extract JSON from markdown code blocks if present
                if "```" in content:
                    # Find the first { and last }
                    start = content.find('{')
                    end = content.rfind('}') + 1
                    json_str = content[start:end]
                else:
                    json_str = content

                return json.loads(json_str)

        except json.JSONDecodeError:
            logger.error(f"Failed to decode AI response: {content}")
            return {
                "status": "ERROR",
                "message": "AI returned invalid JSON"
            }
        except Exception as e:
            logger.error(f"AI Error: {str(e)}")
            return {
                "status": "ERROR",
                "message": f"Thinking Error: {str(e)}"
            }
