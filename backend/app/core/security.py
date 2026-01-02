"""
Input validation utilities for security.
"""
import re
from typing import Optional

def sanitize_string(input_str: str, max_length: int = 1000) -> str:
    """
    Sanitize user input strings.
    - Limit length
    - Remove potentially dangerous characters
    """
    if not input_str:
        return ""
    
    # Truncate to max length
    sanitized = str(input_str)[:max_length]
    
    # Remove control characters and null bytes
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\n\r\t')
    
    return sanitized.strip()

def validate_symbol(symbol: str) -> bool:
    """
    Validate stock symbol format.
    Only alphanumeric and underscore/dash allowed.
    """
    if not symbol or len(symbol) > 20:
        return False
    
    pattern = r'^[A-Z0-9_\-&]+$'
    return bool(re.match(pattern, symbol))

def sanitize_query(query: str) -> Optional[str]:
    """
    Sanitize natural language queries.
    """
    if not query:
        return None
    
    # Limit length for AI queries
    sanitized = sanitize_string(query, max_length=500)
    
    # Ensure minimum length
    if len(sanitized) < 3:
        return None
    
    return sanitized

def validate_portfolio_input(symbol: str, quantity: int, price: float) -> tuple[bool, str]:
    """
    Validate portfolio holding inputs.
    Returns (is_valid, error_message)
    """
    # Symbol validation
    if not symbol or not validate_symbol(symbol):
        return False, "Invalid symbol format"
    
    # Quantity validation
    if quantity <= 0:
        return False, "Quantity must be positive"
    
    if quantity > 1_000_000:  # Upper limit: 1 million shares
        return False, "Quantity exceeds reasonable limit (1M shares)"
    
    # Price validation
    if price <= 0:
        return False, "Price must be positive"
    
    if price > 10_000_000:  # Upper limit: ₹1 Crore per share
        return False, "Price exceeds reasonable limit (₹1Cr/share)"
    
    return True, ""
