#!/usr/bin/env python3
"""Test script to verify AI model response"""
import asyncio
import sys
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.ai import AIAlertInterpreter

async def test_ai():
    ai = AIAlertInterpreter()
    
    test_queries = [
        "Show me chart of Hindalco",
        "Analyze volume of Tata Motors",
        "What is the volume trend of HDFC Bank",
        "Chart for Reliance"
    ]
    
    print("Testing AI Model Responses:\n")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        result = await ai.interpret(query)
        print(f"📊 Response: {result}")
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(test_ai())
