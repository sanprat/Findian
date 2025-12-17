
import asyncio
import logging
import httpx
from app.core.ai import AIAlertInterpreter

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_bulk_add():
    print("🚀 Testing Bulk Portfolio Add...")
    
    # 1. Simulate AI Interpretation (mocking or real? Real is better to test prompt)
    # But since we want to test the full endpoint, let's hit the API directly? 
    # Or just test the logic component. 
    # Let's test the Endpoint logic via requests to localhost if inside container.
    
    url = "http://localhost:8000/api/alert/create"
    query = "Bought 10 TCS at 3000 and 20 INFY at 1500"
    payload = {"user_id": "12345", "query": query}
    
    print(f"📡 Sending Query: '{query}'")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, timeout=60.0)
            print(f"Response Code: {resp.status_code}")
            result = resp.json()
            print("✅ Result:", result)
            
            if result.get("status") == "PORTFOLIO_ADDED":
                msg = result.get("message", "")
                if "TCS" in msg and "INFY" in msg:
                    print("🎉 Success! Both stocks detected and added.")
                else:
                    print("⚠️ Partial success? Message:", msg)
            else:
                print("❌ Failed or unexpected status.")
                
        except Exception as e:
            print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_bulk_add())
