
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# MOCK DEPENDENCIES BEFORE IMPORT
sys.modules["NorenRestApiPy"] = MagicMock()
sys.modules["NorenRestApiPy.NorenApi"] = MagicMock()

from app.core.ai import AIAlertInterpreter
from app.core.market_data import MarketDataService

# --- TEST AI INTERPRETER ---
@pytest.mark.asyncio
async def test_ai_interpret_create_alert():
    ai = AIAlertInterpreter()
    
    # Mock the _call_with_fallback method to avoid real API calls
    mock_response = {
        "intent": "CREATE_ALERT",
        "status": "CONFIRMED",
        "config": {"symbol": "TCS", "conditions": [{"type": "ltp", "operator": "gt", "value": 3000}]}
    }
    
    with patch.object(ai, '_call_with_fallback', return_value=mock_response) as mock_call:
        result = await ai.interpret("Alert me if TCS crosses 3000")
        
        assert result["intent"] == "CREATE_ALERT"
        assert result["status"] == "CONFIRMED"
        assert result["config"]["symbol"] == "TCS"
        mock_call.assert_called_once()

@pytest.mark.asyncio
async def test_ai_interpret_rejection():
    ai = AIAlertInterpreter()
    mock_response = {
        "status": "REJECTED",
        "message": "I am an AI tool..."
    }
    with patch.object(ai, '_call_with_fallback', return_value=mock_response):
        result = await ai.interpret("What stocks should I buy?")
        assert result["status"] == "REJECTED"

# --- TEST MARKET DATA SERVICE ---
def test_market_data_get_quote_mock():
    md = MarketDataService()
    
    # Mock NorenApi
    md.api = MagicMock()
    md.is_connected = True
    
    # Mock minimal response
    mock_search = [{'token': '1234', 'tsym': 'TCS-EQ'}]
    md.api.searchscrip.return_value = mock_search
    
    mock_quote = {'stat': 'Ok', 'lp': '3500.00', 'c': '3450.00', 'v': '1000'}
    md.api.get_quotes.return_value = mock_quote
    
    quote = md.get_quote("TCS")
    
    assert quote is not None
    assert quote["symbol"] == "TCS"
    # Note: MarketDataService might handle searchtext="TCS" by searching and finding TCS-EQ
    # The float conversion happens in get_quote
    assert quote["ltp"] == 3500.0
    assert quote["close"] == 3450.0
