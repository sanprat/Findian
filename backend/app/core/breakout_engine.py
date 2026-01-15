import logging
import json
from datetime import datetime
from app.core.cache import cache
# from app.core.alert_dispatcher import AlertDispatcher # To be implemented

logger = logging.getLogger(__name__)

class BreakoutEngine:
    """
    Analyzes real-time ticks to detect breakout patterns.
    Primary Logic:
    1. Price > 52-Week High
    2. Volume > 2x Average (20-day) Volume
    """
    
    def __init__(self, dispatcher=None):
        self.dispatcher = dispatcher  # AlertDispatcher instance
        self.alert_cooldowns = {}      # Local memory for immediate dedup (optional)

    async def process_tick(self, tick_data: dict):
        """
        Process a single tick from WebSocket.
        Expected format: {token, ltp, volume, timestamp, ...}
        """
        try:
            symbol = self._get_symbol_from_token(tick_data.get('token'))
            if not symbol:
                return

            ltp = float(tick_data.get('ltp', 0))
            volume = float(tick_data.get('volume', 0))
            
            # 1. Fetch Key Stats from Redis (Cached by Scanner/Scheduler)
            # Keys: stock:{symbol}:stats -> {high_52w, avg_volume}
            stats = await cache.get(f"stock:{symbol}:stats")
            
            if not stats:
                # If stats missing, we can't judge breakout. 
                # (Optional: Trigger background fetch)
                return

            stats_dict = json.loads(stats)
            high_52w = float(stats_dict.get('high_52w', 999999))
            avg_volume = float(stats_dict.get('avg_volume', 99999999)) # Default high to avoid false pos

            # 2. Breakout Logic
            is_price_breakout = ltp > high_52w
            is_vol_breakout = volume > (avg_volume * 1.5) # Reduced to 1.5x for sensitivity

            if is_price_breakout and is_vol_breakout:
                await self._trigger_alert(symbol, ltp, volume, high_52w, avg_volume)
                
        except Exception as e:
            logger.error(f"Error processing tick for breakout: {e}")

    async def _trigger_alert(self, symbol, ltp, volume, high_52w, avg_volume):
        """
        Dispatch alert if not on cooldown.
        """
        # Redis-based cooldown check (distributed)
        cooldown_key = f"alert_cooldown:{symbol}:breakout"
        is_cooldown = await cache.get(cooldown_key)
        
        if is_cooldown:
            return

        logger.info(f"🚀 BREAKOUT DETECTED: {symbol} @ {ltp} (Vol: {volume})")
        
        # Set cooldown (e.g., 60 mins)
        await cache.set(cooldown_key, "1", ttl=3600)
        
        if self.dispatcher:
            payload = {
                "type": "BREAKOUT",
                "symbol": symbol,
                "price": ltp,
                "volume": volume,
                "reason": f"Crossed 52W High ({high_52w}) with High Volume",
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.dispatcher.dispatch(payload)
    
    def _get_symbol_from_token(self, token):
        # Helper to bridge token -> symbol
        # Ideally, this map is also in Redis or memory
        from app.core.symbol_tokens import get_symbol
        return get_symbol(str(token))
