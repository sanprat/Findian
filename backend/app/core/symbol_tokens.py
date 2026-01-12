"""
Symbol to Token Mapping for Angel One SmartAPI
Maps NSE stock symbols to their trading tokens
"""

# Top NSE stocks with their SmartAPI tokens
# Source: Angel One instrument master file
SYMBOL_TO_TOKEN = {
    # NIFTY 50 Stocks
    "RELIANCE": "2885",
    "TCS": "11536",
    "HDFCBANK": "1333",
    "INFY": "1594",
    "ICICIBANK": "4963",
    "HINDUNILVR": "1394",
    "ITC": "1660",
    "SBIN": "3045",
    "BHARTIARTL": "10604",
    "BAJFINANCE": "317",
    "KOTAKBANK": "1922",
    "LT": "11483",
    "HCLTECH": "7229",
    "ASIANPAINT": "236",
    "AXISBANK": "5900",
    "MARUTI": "10999",
    "SUNPHARMA": "3351",
    "TITAN": "3506",
    "ULTRACEMCO": "11532",
    "NESTLEIND": "17963",
    "WIPRO": "3787",
    "DMART": "14299",
    "BAJAJFINSV": "16675",
    "POWERGRID": "14977",
    "NTPC": "11630",
    "TATASTEEL": "3499",
    "TECHM": "13538",
    "ADANIPORTS": "15083",
    "ONGC": "2475",
    "COALINDIA": "20374",
    "JSWSTEEL": "11723",
    "INDUSINDBK": "5258",
    "HINDALCO": "1363",
    "GRASIM": "1232",
    "DIVISLAB": "10940",
    "BRITANNIA": "547",
    "HEROMOTOCO": "1348",
    "EICHERMOT": "910",
    "CIPLA": "694",
    "DRREDDY": "881",
    "APOLLOHOSP": "157",
    "SHREECEM": "3103",
    "SBILIFE": "21808",
    "HDFCLIFE": "467",
    "BAJAJ-AUTO": "16669",
    "TATACONSUM": "3432",
    "M&M": "2031",
    "UPL": "11287",
    
    # Fixed symbols (were failing)
    "LTIM": "17818",  # Was LTI - merged to LTIMindtree
    "TATAMOTORS": "3456",  # Fixed token
    "ADANIENT": "25",
    "BPCL": "526",
    
    # Bank Nifty Additional
    "BANDHANBNK": "2263",
    "FEDERALBNK": "1023",
    "IDFCFIRSTB": "11184",
    "PNB": "10666",
    
    # Additional Popular Stocks
    "ZOMATO": "5097",
    "PAYTM": "6705",
    "NYKAA": "17558",
    "IRCTC": "13611",
    "TATAPOWER": "3426",
    "ADANIGREEN": "15202",
    "VEDL": "3063",
    "JINDALSTEL": "6733",
    "SAIL": "2963",
    "NMDC": "15332",
    "SBICARD": "41688",
    "PIDILITIND": "2664",
    "SIEMENS": "3150",
    "HAVELLS": "9819",
    "MOTHERSON": "4204",
}

# Reverse mapping for quick lookups
TOKEN_TO_SYMBOL = {v: k for k, v in SYMBOL_TO_TOKEN.items()}


def get_token(symbol: str) -> str:
    """Get SmartAPI token for a symbol"""
    return SYMBOL_TO_TOKEN.get(symbol.upper())


def get_symbol(token: str) -> str:
    """Get symbol from SmartAPI token"""
    return TOKEN_TO_SYMBOL.get(token)


def get_all_tokens() -> list:
    """Get list of all tracked tokens"""
    return list(SYMBOL_TO_TOKEN.values())


def get_all_symbols() -> list:
    """Get list of all tracked symbols"""
    return list(SYMBOL_TO_TOKEN.keys())
