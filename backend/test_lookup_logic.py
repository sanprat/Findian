from unittest.mock import MagicMock
from app.core.lookup import SymbolLookup
from app.db.models import Stock

# Mock DB Session
mock_db = MagicMock()

# Mock Data
mock_stocks = [
    Stock(symbol="RELIANCE", name="Reliance Industries Ltd", is_active=True),
    Stock(symbol="ELECON", name="Elecon Engineering Company Ltd", is_active=True),
    Stock(symbol="TATAMOTORS", name="Tata Motors Limited", is_active=True),
    Stock(symbol="INFY", name="Infosys Limited", is_active=True),
]

# Configure Mock
mock_db.query.return_value.filter.return_value.all.return_value = mock_stocks

def test_lookup():
    print("🧪 Testing Smart Lookup Logic...")
    lookup = SymbolLookup(mock_db)
    
    test_cases = [
        ("Elecon Eng", "ELECON"),
        ("Tata Mot", "TATAMOTORS"),
        ("Relianc", "RELIANCE"),
        ("Infosys", "INFY"),
        ("Unknown Stock XYZ", "UNKNOWN STOCK XYZ") # Should return original uppercase
    ]
    
    for query, expected in test_cases:
        result = lookup.resolve(query)
        status = "✅" if result == expected else "❌"
        print(f"{status} Query: '{query}' -> Result: '{result}' (Expected: '{expected}')")

if __name__ == "__main__":
    test_lookup()
