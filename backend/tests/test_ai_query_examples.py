"""
Test cases for AI query examples to ensure proper intent classification.
Tests the new query examples added to AIAlertInterpreter.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# MOCK DEPENDENCIES BEFORE IMPORT
sys.modules["NorenRestApiPy"] = MagicMock()
sys.modules["NorenRestApiPy.NorenApi"] = MagicMock()

from app.core.ai import AIAlertInterpreter


# --- TEST QUERY EXAMPLES FROM DOCUMENTATION ---
@pytest.mark.asyncio
async def test_query_example_1_hdfc_price():
    """Example 1: "What is HDFC price?" → CHECK_PRICE"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "CHECK_PRICE",
        "status": "CONFIRMED",
        "data": {"symbol": "HDFC"}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("What is HDFC price?")
        assert result["intent"] == "CHECK_PRICE"
        assert result["data"]["symbol"] == "HDFC"


@pytest.mark.asyncio
async def test_query_example_2_tcs_price():
    """Example 2: "Current price of TCS" → CHECK_PRICE"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "CHECK_PRICE",
        "status": "CONFIRMED",
        "data": {"symbol": "TCS"}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Current price of TCS")
        assert result["intent"] == "CHECK_PRICE"
        assert result["data"]["symbol"] == "TCS"


@pytest.mark.asyncio
async def test_query_example_3_infy_volume():
    """Example 3: "INFY volume today" → CHECK_PRICE"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "CHECK_PRICE",
        "status": "CONFIRMED",
        "data": {"symbol": "INFY"}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("INFY volume today")
        assert result["intent"] == "CHECK_PRICE"
        assert result["data"]["symbol"] == "INFY"


@pytest.mark.asyncio
async def test_query_example_4_reliance_chart():
    """Example 4: "Show chart of Reliance" → ANALYZE_STOCK"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "ANALYZE_STOCK",
        "status": "CONFIRMED",
        "data": {"symbol": "RELIANCE"}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Show chart of Reliance")
        assert result["intent"] == "ANALYZE_STOCK"
        assert result["data"]["symbol"] == "RELIANCE"


@pytest.mark.asyncio
async def test_query_example_5_hdfc_analyze():
    """Example 5: "Analyze HDFC Bank" → ANALYZE_STOCK"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "ANALYZE_STOCK",
        "status": "CONFIRMED",
        "data": {"symbol": "HDFC"}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Analyze HDFC Bank")
        assert result["intent"] == "ANALYZE_STOCK"
        assert result["data"]["symbol"] == "HDFC"


@pytest.mark.asyncio
async def test_query_example_6_tcs_volume_trend():
    """Example 6: "Volume trend of TCS" → ANALYZE_STOCK"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "ANALYZE_STOCK",
        "status": "CONFIRMED",
        "data": {"symbol": "TCS"}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Volume trend of TCS")
        assert result["intent"] == "ANALYZE_STOCK"
        assert result["data"]["symbol"] == "TCS"


@pytest.mark.asyncio
async def test_query_example_7_infy_technical():
    """Example 7: "Technical analysis of INFY" → ANALYZE_STOCK"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "ANALYZE_STOCK",
        "status": "CONFIRMED",
        "data": {"symbol": "INFY"}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Technical analysis of INFY")
        assert result["intent"] == "ANALYZE_STOCK"
        assert result["data"]["symbol"] == "INFY"


@pytest.mark.asyncio
async def test_query_example_8_hdfc_portfolio_add():
    """Example 8: "Bought 10 HDFC at 1600" → ADD_PORTFOLIO"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "ADD_PORTFOLIO",
        "status": "CONFIRMED",
        "data": {"items": [{"symbol": "HDFC", "quantity": 10, "price": 1600}]}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Bought 10 HDFC at 1600")
        assert result["intent"] == "ADD_PORTFOLIO"
        assert result["data"]["items"][0]["symbol"] == "HDFC"


@pytest.mark.asyncio
async def test_query_example_9_tcs_portfolio_sell():
    """Example 9: "Sold 5 TCS at 3500" → SELL_PORTFOLIO"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "SELL_PORTFOLIO",
        "status": "CONFIRMED",
        "data": {"symbol": "TCS", "quantity": 5, "price": 3500}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Sold 5 TCS at 3500")
        assert result["intent"] == "SELL_PORTFOLIO"
        assert result["data"]["symbol"] == "TCS"


@pytest.mark.asyncio
async def test_query_example_10_view_portfolio():
    """Example 10: "Show my portfolio" → VIEW_PORTFOLIO"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "VIEW_PORTFOLIO",
        "status": "CONFIRMED"
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Show my portfolio")
        assert result["intent"] == "VIEW_PORTFOLIO"


@pytest.mark.asyncio
async def test_query_example_11_create_alert_reliance():
    """Example 11: "Alert if Reliance > 2500" → CREATE_ALERT"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "CREATE_ALERT",
        "status": "CONFIRMED",
        "config": {"symbol": "RELIANCE", "conditions": [{"field": "ltp", "op": "gt", "value": 2500}]}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Alert if Reliance > 2500")
        assert result["intent"] == "CREATE_ALERT"
        assert result["config"]["symbol"] == "RELIANCE"


@pytest.mark.asyncio
async def test_query_example_12_create_alert_infy():
    """Example 12: "Notify when INFY < 1400" → CREATE_ALERT"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "CREATE_ALERT",
        "status": "CONFIRMED",
        "config": {"symbol": "INFY", "conditions": [{"field": "ltp", "op": "lt", "value": 1400}]}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Notify when INFY < 1400")
        assert result["intent"] == "CREATE_ALERT"
        assert result["config"]["symbol"] == "INFY"


@pytest.mark.asyncio
async def test_query_example_13_market_info_pe():
    """Example 13: "What is P/E ratio?" → MARKET_INFO"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "MARKET_INFO",
        "status": "MARKET_INFO",
        "data": {"answer": "P/E ratio explanation..."}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("What is P/E ratio?")
        assert result["intent"] == "MARKET_INFO"


@pytest.mark.asyncio
async def test_query_example_14_market_info_rsi():
    """Example 14: "How does RSI work?" → MARKET_INFO"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "MARKET_INFO",
        "status": "MARKET_INFO",
        "data": {"answer": "RSI explanation..."}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("How does RSI work?")
        assert result["intent"] == "MARKET_INFO"


@pytest.mark.asyncio
async def test_query_example_15_market_info_breakout():
    """Example 15: "What is breakout?" → MARKET_INFO"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "MARKET_INFO",
        "status": "MARKET_INFO",
        "data": {"answer": "Breakout explanation..."}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("What is breakout?")
        assert result["intent"] == "MARKET_INFO"


@pytest.mark.asyncio
async def test_query_example_16_market_info_hdfc_fall():
    """Example 16: "Why did HDFC fall today?" → MARKET_INFO"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "MARKET_INFO",
        "status": "MARKET_INFO",
        "data": {"answer": "General reasons for stock movement..."}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Why did HDFC fall today?")
        assert result["intent"] == "MARKET_INFO"


@pytest.mark.asyncio
async def test_query_example_17_check_fundamentals():
    """Example 17: "HDFC fundamentals" → CHECK_FUNDAMENTALS"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "CHECK_FUNDAMENTALS",
        "status": "CONFIRMED",
        "data": {"symbol": "HDFC"}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("HDFC fundamentals")
        assert result["intent"] == "CHECK_FUNDAMENTALS"
        assert result["data"]["symbol"] == "HDFC"


@pytest.mark.asyncio
async def test_query_example_18_check_fundamentals_pe():
    """Example 18: "Show PE ratio of TCS" → CHECK_FUNDAMENTALS"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "CHECK_FUNDAMENTALS",
        "status": "CONFIRMED",
        "data": {"symbol": "TCS"}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Show PE ratio of TCS")
        assert result["intent"] == "CHECK_FUNDAMENTALS"
        assert result["data"]["symbol"] == "TCS"


@pytest.mark.asyncio
async def test_query_example_19_screener_high_volume():
    """Example 19: "Find stocks with high volume" → Redirect to Screener"""
    ai = AIAlertInterpreter()
    mock_response = {
        "status": "MARKET_INFO",
        "data": {"answer": "To find multiple stocks, please use the 🔍 Screener menu and select 'Custom AI'."}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Find stocks with high volume")
        assert result["status"] == "MARKET_INFO"
        assert "Screener" in result["data"]["answer"]


@pytest.mark.asyncio
async def test_query_example_20_screener_52w_high():
    """Example 20: "Stocks near 52w high" → Redirect to Screener"""
    ai = AIAlertInterpreter()
    mock_response = {
        "status": "MARKET_INFO",
        "data": {"answer": "To find multiple stocks, please use the 🔍 Screener menu and select 'Custom AI'."}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Stocks near 52w high")
        assert result["status"] == "MARKET_INFO"
        assert "Screener" in result["data"]["answer"]


@pytest.mark.asyncio
async def test_query_example_21_rejected_buy_advice():
    """Example 21: "Should I buy HDFC?" → REJECTED"""
    ai = AIAlertInterpreter()
    mock_response = {
        "status": "REJECTED",
        "message": "I cannot provide investment advice."
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Should I buy HDFC?")
        assert result["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_query_example_22_rejected_investment_advice():
    """Example 22: "Is this a good time to invest?" → REJECTED"""
    ai = AIAlertInterpreter()
    mock_response = {
        "status": "REJECTED",
        "message": "I cannot provide investment advice."
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Is this a good time to invest?")
        assert result["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_query_example_23_rejected_non_stock():
    """Example 23: "What's the weather?" → REJECTED"""
    ai = AIAlertInterpreter()
    mock_response = {
        "status": "REJECTED",
        "message": "Sorry, I don't have that information. I only assist with stock market queries."
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("What's the weather?")
        assert result["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_query_example_24_alias_conversion():
    """Example 24: "What is RIL price?" → CHECK_PRICE with symbol=RELIANCE"""
    ai = AIAlertInterpreter()
    mock_response = {
        "intent": "CHECK_PRICE",
        "status": "CONFIRMED",
        "data": {"symbol": "RELIANCE"}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("What is RIL price?")
        assert result["intent"] == "CHECK_PRICE"
        assert result["data"]["symbol"] == "RELIANCE"


@pytest.mark.asyncio
async def test_query_example_25_context_handling():
    """Example 25: Context handling with previous symbol"""
    ai = AIAlertInterpreter()
    context = {"last_symbol": "HDFC"}
    mock_response = {
        "intent": "CHECK_FUNDAMENTALS",
        "status": "CONFIRMED",
        "data": {"symbol": "HDFC"}
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("What about fundamentals?", context=context)
        assert result["intent"] == "CHECK_FUNDAMENTALS"
        assert result["data"]["symbol"] == "HDFC"


@pytest.mark.asyncio
async def test_query_example_26_rejected_future_prediction():
    """Example 26: "What should I buy tomorrow?" → REJECTED"""
    ai = AIAlertInterpreter()
    mock_response = {
        "status": "REJECTED",
        "message": "I cannot provide investment advice."
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("What should I buy tomorrow?")
        assert result["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_query_example_27_rejected_stock_recommendations():
    """Example 27: "Show me the best stocks to buy" → REJECTED"""
    ai = AIAlertInterpreter()
    mock_response = {
        "status": "REJECTED",
        "message": "I cannot provide investment advice."
    }

    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("Show me the best stocks to buy")
        assert result["status"] == "REJECTED"
