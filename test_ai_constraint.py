#!/usr/bin/env python3
"""Test AI with stock and non-stock queries"""
import asyncio
import sys
import os

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.ai import AIAlertInterpreter

async def test_ai():
    ai = AIAlertInterpreter()
    
    print("=" * 70)
    print("TESTING AI STOCK MARKET CONSTRAINT")
    print("=" * 70)
    
    # Test stock market queries (should work)
    stock_queries = [
        "What is the price of HDFC?",
        "Show fundamentals of TCS",
        "What is RSI?",
        "Bought 10 INFY at 1400"
    ]
    
    # Test non-stock queries (should reject)
    non_stock_queries = [
        "What is the weather today?",
        "Tell me a recipe for pasta",
        "Who is the president of India?",
        "What is Python programming?"
    ]
    
    print("\n📊 STOCK MARKET QUERIES (Should Work):\n")
    for query in stock_queries:
        print(f"Query: '{query}'")
        result = await ai.interpret(query)
        status = result.get('status')
        intent = result.get('intent')
        message = result.get('message', '')
        print(f"✅ Status: {status}, Intent: {intent}")
        if message:
            print(f"   Message: {message}")
        print()
    
    print("\n" + "=" * 70)
    print("❌ NON-STOCK QUERIES (Should Reject):\n")
    for query in non_stock_queries:
        print(f"Query: '{query}'")
        result = await ai.interpret(query)
        status = result.get('status')
        message = result.get('message', '')
        
        if status == "REJECTED":
            print(f"✅ CORRECTLY REJECTED")
        else:
            print(f"❌ FAILED - Status: {status}")
        
        print(f"   Message: {message}")
        print()
    
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_ai())
