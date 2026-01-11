"""
Input validation and security utilities.
"""
import re
import hmac
import hashlib
import logging
import functools
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger("security")

# --- Constants for Validation ---
# Telegram user IDs are positive integers up to 52 bits
TELEGRAM_USER_ID_MAX = 2**52 - 1
TELEGRAM_USER_ID_MIN = 1

# Stock symbol pattern: Alphanumeric, underscore, hyphen, ampersand
# Max 20 chars, must start with letter
SYMBOL_PATTERN = re.compile(r'^[A-Z][A-Z0-9_\-&]{0,19}$')

# Maximum lengths for various inputs
MAX_QUERY_LENGTH = 500
MAX_STRING_LENGTH = 1000
MAX_SYMBOL_LENGTH = 20


def sanitize_string(input_str: str, max_length: int = MAX_STRING_LENGTH) -> str:
    """
    Sanitize user input strings.
    - Limit length
    - Remove potentially dangerous characters
    - Strip control characters
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
    - Must start with a letter
    - Only alphanumeric, underscore, hyphen, and ampersand allowed
    - Maximum 20 characters
    """
    if not symbol or len(symbol) > MAX_SYMBOL_LENGTH:
        return False
    
    return bool(SYMBOL_PATTERN.match(symbol.upper()))


def validate_user_id(user_id: str | int) -> Tuple[bool, Optional[int]]:
    """
    Validate Telegram user ID.
    Returns (is_valid, parsed_id).
    
    SECURITY: Validates that user_id is a valid Telegram ID:
    - Must be a positive integer
    - Must be within valid Telegram ID range (1 to 2^52-1)
    """
    try:
        if isinstance(user_id, str):
            # Strip whitespace and validate it's numeric
            user_id = user_id.strip()
            if not user_id.isdigit():
                return False, None
            parsed_id = int(user_id)
        else:
            parsed_id = int(user_id)
        
        # Validate range
        if TELEGRAM_USER_ID_MIN <= parsed_id <= TELEGRAM_USER_ID_MAX:
            return True, parsed_id
        
        return False, None
    except (ValueError, TypeError, OverflowError):
        return False, None


def sanitize_query(query: str) -> Optional[str]:
    """
    Sanitize natural language queries.
    """
    if not query:
        return None
    
    # Limit length for AI queries
    sanitized = sanitize_string(query, max_length=MAX_QUERY_LENGTH)
    
    # Ensure minimum length
    if len(sanitized) < 3:
        return None
    
    return sanitized


def validate_portfolio_input(symbol: str, quantity: int, price: float) -> Tuple[bool, str]:
    """
    Validate portfolio holding inputs.
    Returns (is_valid, error_message)
    """
    # Symbol validation
    if not symbol or not validate_symbol(symbol):
        return False, "Invalid symbol format"
    
    # Quantity validation
    if not isinstance(quantity, (int, float)) or quantity <= 0:
        return False, "Quantity must be positive"
    
    if quantity > 1_000_000:  # Upper limit: 1 million shares
        return False, "Quantity exceeds reasonable limit (1M shares)"
    
    # Price validation
    if not isinstance(price, (int, float)) or price <= 0:
        return False, "Price must be positive"
    
    if price > 10_000_000:  # Upper limit: ₹1 Crore per share
        return False, "Price exceeds reasonable limit (₹1Cr/share)"
    
    return True, ""


def secure_compare(a: str, b: str) -> bool:
    """
    SECURITY: Timing-safe string comparison to prevent timing attacks.
    Use this for comparing secrets/tokens.
    """
    # Hash both values first to ensure equal length comparison
    a_hash = hashlib.sha256(a.encode()).digest()
    b_hash = hashlib.sha256(b.encode()).digest()
    return hmac.compare_digest(a_hash, b_hash)


def audit_log(action: str):
    """
    Decorator for audit logging sensitive operations.
    
    Usage:
        @audit_log("DELETE_PORTFOLIO")
        def delete_portfolio(user_id, symbol):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            user_id = kwargs.get('user_id') or (args[0] if args else 'unknown')
            try:
                result = await func(*args, **kwargs)
                logger.info(
                    f"AUDIT: action={action} user_id={user_id} "
                    f"status=SUCCESS duration_ms={(datetime.utcnow() - start_time).total_seconds() * 1000:.2f}"
                )
                return result
            except Exception as e:
                logger.warning(
                    f"AUDIT: action={action} user_id={user_id} "
                    f"status=FAILED error={type(e).__name__}"
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            user_id = kwargs.get('user_id') or (args[0] if args else 'unknown')
            try:
                result = func(*args, **kwargs)
                logger.info(
                    f"AUDIT: action={action} user_id={user_id} "
                    f"status=SUCCESS duration_ms={(datetime.utcnow() - start_time).total_seconds() * 1000:.2f}"
                )
                return result
            except Exception as e:
                logger.warning(
                    f"AUDIT: action={action} user_id={user_id} "
                    f"status=FAILED error={type(e).__name__}"
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def sanitize_error_message(error: Exception) -> str:
    """
    SECURITY: Sanitize error messages to prevent information leakage.
    Returns a generic message instead of exposing internal details.
    """
    error_type = type(error).__name__
    
    # Map specific errors to user-friendly messages
    safe_messages = {
        "ValueError": "Invalid input provided",
        "KeyError": "Missing required field",
        "TypeError": "Invalid data type",
        "OperationalError": "Database temporarily unavailable",
        "IntegrityError": "Data conflict - please try again",
        "TimeoutError": "Request timed out",
        "ConnectionError": "Service temporarily unavailable",
    }
    
    return safe_messages.get(error_type, "An error occurred. Please try again.")
