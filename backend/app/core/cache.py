import os
import logging
from redis import asyncio as aioredis
from typing import Optional

logger = logging.getLogger(__name__)

class CacheService:
    _instance = None
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.password = os.getenv("REDIS_PASSWORD", None)

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    async def connect(self):
        """Initialize Redis connection pool"""
        if self.redis:
            return

        try:
            # Construct URL or use kwargs
            # If using Railway, REDIS_URL might be provided, or individual vars
            redis_url = os.getenv("REDIS_URL")
            
            if redis_url:
                self.redis = aioredis.from_url(redis_url, decode_responses=True)
                logger.info("✅ Connected to Redis via URL")
            else:
                self.redis = aioredis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    decode_responses=True,
                    socket_timeout=5.0
                )
                logger.info(f"✅ Connected to Redis at {self.host}:{self.port}")
                
            # Ping to verify
            await self.redis.ping()
            
        except Exception as e:
            logger.error(f"❌ Redis Connection Failed: {e}")
            self.redis = None
            # Don't raise - allow app to start without cache (graceful degradation)

    async def close(self):
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")

    async def get(self, key: str):
        if not self.redis: return None
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = None):
        if not self.redis: return False
        try:
            return await self.redis.set(key, value, ex=ttl)
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False

    async def delete(self, key: str):
        if not self.redis: return False
        try:
            return await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False

    def is_healthy(self) -> bool:
        return self.redis is not None

# Global instance
cache = CacheService.get_instance()
