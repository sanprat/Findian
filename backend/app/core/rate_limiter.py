
import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse
import logging
from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.db.models import User
import json

logger = logging.getLogger(__name__)

# Initialize Limiter
# Using Redis if available, else Memory
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
limiter = Limiter(key_func=get_remote_address, storage_uri=redis_url)

def get_user_id_from_request(request: Request) -> str:
    """
    Extract user_id from request body for rate limiting.
    CAUTION: This consumes/reads the request body. 
    Starlette caches it so subsequent reads are safe.
    """
    # For GET requests, try query params
    if request.method == "GET":
        return request.query_params.get("user_id", get_remote_address(request))
    
    # For POST, try JSON body
    try:
        # We need to await this in an async context, but key_func is sync in slowapi defaults?
        # Check if limits supports async key_func. 
        # Actually, slowapi key_func is typically sync.
        # But we can't easily read async body in sync func.
        # Fallback: Use remote address for now if body read is hard, 
        # OR relies on the fact that we might move this to a dependency.
        
        # Strategy: Use a dependency for rate limiting instead of decorator if we need body.
        # But let's try to see if we can get it. 
        # For now, let's fall back to IP if we can't get ID, but this is flawed for a bot proxy.
        # Since all requests come from the Bot Container IP, IP limiting is useless!
        # We MUST use user_id.
        return "global_bot_user" # Placeholder, actual logic moved to dependency
    except:
        return get_remote_address(request)

# Define Quotas
TIER_QUOTAS = {
    "FREE": "10/day",
    "PRO": "100/day",
    "PREMIUM": "1000/day",
    "ADMIN": "1000000/day" # Effectively unlimited
}

def get_limit_key(user_id: str) -> str:
    return user_id

def check_rate_limit(user_id: str, db: Session) -> tuple[bool, str]:
    """
    Manual check function to be used inside endpoints.
    Returns (allowed: bool, limit_msg: str)
    """
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        tier = user.subscription_tier if user else "FREE"
        limit_str = TIER_QUOTAS.get(tier, "10/day")
        
        # Use the underlying limiter storage to check manually
        # This is a bit complex with slowapi's internals.
        # Alternative: We Just use Redis directly for a simple counters implementation 
        # since we have Redis and simple requirements.
        # This is likely more robust than wrestling slowapi for body-based limits behind a proxy.
        
        return True, limit_str # Placeholder for the manual logic below
    except Exception as e:
        logger.error(f"Rate limit check error: {e}")
        return True, "10/day" # Fail open

# --- CUSTOM REDIS RATE LIMITER (Simpler for Bot use case) ---
import redis
import time

class TierRateLimiter:
    def __init__(self):
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        
    def is_allowed(self, user_id: str, tier: str) -> bool:
        """
        Checks if user is allowed based on daily quota.
        """
        limit_count = 10
        if tier == "PRO": limit_count = 100
        elif tier == "PREMIUM": limit_count = 1000
        
        key = f"rate_limit:{user_id}:{time.strftime('%Y-%m-%d')}"
        
        current = self.redis.get(key)
        if current and int(current) >= limit_count:
            return False
            
        self.redis.incr(key)
        # Set expiry for 24 hours (cleanup)
        self.redis.expire(key, 86400)
        
        return True

    def get_usage(self, user_id: str) -> int:
        """Returns the current usage count for today."""
        key = f"rate_limit:{user_id}:{time.strftime('%Y-%m-%d')}"
        current = self.redis.get(key)
        return int(current) if current else 0

custom_limiter = TierRateLimiter()
