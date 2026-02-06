import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.app.core.tools import TavilyClient

def test_tavily():
    print("🔄 Testing Tavily Search with Real Keys...")
    client = TavilyClient()
    
    if not client.available_keys:
        print("❌ No keys found in environment!")
        return
        
    print(f"✅ Found {len(client.available_keys)} keys.")
    
    # Try search
    try:
        result = client.search_news("Stock market today")
        if "Latest News" in result or "No recent news" in result:
            print("✅ Tavily Search Successful!")
            print(f"Sample Output: {result[:100]}...")
        else:
            print(f"⚠️ Unexpected output format: {result[:100]}...")
    except Exception as e:
        print(f"❌ Tavily Search Failed: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv() # Load .env from root
    test_tavily()
