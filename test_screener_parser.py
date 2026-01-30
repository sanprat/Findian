#!/usr/bin/env python3
"""Test screener query parsing with unsupported fields"""
import asyncio
import sys
import os

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.ai import AIAlertInterpreter

async def test_screener():
    ai = AIAlertInterpreter()
    
    print("=" * 70)
    print("TESTING SCREENER QUERY PARSING")
    print("=" * 70)
    
    queries = [
        # Should work
        "stocks with high volume",
        "RSI below 30",
        "price above 1000 and volume greater than 500000",
        
        # Should return helpful error
        "stocks near 52 week high",
        "stocks with 52w high with volume",
        "stocks with low P/E ratio",
        "find stocks with high market cap"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        result = await ai.parse_screener_query(query)
        
        if result.get("filters"):
            print(f"✅ Filters: {result['filters']}")
        elif result.get("error"):
            error_type = result.get("error")
            message = result.get("message", "")
            print(f"ℹ️  Error: {error_type}")
            if message:
                print(f"   Message: {message}")
        else:
            print(f"⚠️  Unexpected: {result}")
        
    print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(test_screener())
