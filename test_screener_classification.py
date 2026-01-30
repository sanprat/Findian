#!/usr/bin/env python3
"""Test screener query classification"""
import asyncio
import sys
import os

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.ai import AIAlertInterpreter

async def test_screener_classification():
    ai = AIAlertInterpreter()
    
    print("=" * 70)
    print("TESTING SCREENER VS ANALYSIS CLASSIFICATION")
    print("=" * 70)
    
    # Screener queries (should redirect to screener menu)
    screener_queries = [
        "show me some stocks with breakout volume",
        "find stocks with high volume",
        "list stocks with RSI below 30",
        "stocks near 52 week high"
    ]
    
    # Analysis queries (should work with ANALYZE_STOCK)
    analysis_queries = [
        "analyze HDFC",
        "show chart of TCS",
        "volume trend of Reliance",
        "technical analysis of INFY"
    ]
    
    print("\n🔍 SCREENER QUERIES (Should redirect to Screener menu):\n")
    for query in screener_queries:
        print(f"Query: '{query}'")
        result = await ai.interpret(query)
        status = result.get('status')
        answer = result.get('data', {}).get('answer', '')
        print(f"Status: {status}")
        if answer:
            print(f"Answer: {answer}")
        print()
    
    print("\n" + "=" * 70)
    print("📊 ANALYSIS QUERIES (Should return ANALYZE_STOCK with symbol):\n")
    for query in analysis_queries:
        print(f"Query: '{query}'")
        result = await ai.interpret(query)
        status = result.get('status')
        intent = result.get('intent')
        symbol = result.get('data', {}).get('symbol', 'N/A')
        print(f"Status: {status}, Intent: {intent}, Symbol: {symbol}")
        print()
    
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_screener_classification())
