import logging
import os
import httpx
from datetime import datetime
from app.core.cache import cache

logger = logging.getLogger(__name__)

class AlertDispatcher:
    """
    Dispatches alerts to subscribed users via Telegram.
    """
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            logger.warning("⚠️ TELEGRAM_BOT_TOKEN missing in Backend. Alerts will not send.")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def dispatch(self, payload: dict):
        """
        Main entry point.
        Payload: {type, symbol, price, volume, reason, timestamp}
        """
        symbol = payload.get("symbol")
        alert_type = payload.get("type", "ALERT")
        
        # 1. Find interested users
        # For MVP: Send to all users who have subscribed or special admin list
        # Ideal: Look up 'watchlists' in Redis/DB.
        # Temp: Users stored in a set "subscribers:all" or similar?
        # Actually, let's just fetch all users from DB or use a broadcast list for Breakouts.
        
        # For Breakouts (High Importance), maybe broadcast to "Pro" users?
        # Let's assume we target a specific list for now to avoid spam.
        # Or, we can query the DB. Since this is async, we should use a service.
        
        # Let's try to get users from Redis who are watching this stock.
        # Key: "watchlist:{symbol}" -> Set of user_ids
        subscribers = await cache.redis.smembers(f"watchlist:{symbol}")
        
        # Also 'global' breakout subscribers?
        # Key: "subscribers:breakouts" -> Set of user_ids
        global_subs = await cache.redis.smembers("subscribers:breakouts")
        
        # Combine
        user_ids = set()
        if subscribers: user_ids.update(subscribers)
        if global_subs: user_ids.update(global_subs)
        
        # If no one watching, maybe log and debug?
        if not user_ids:
            # logger.debug(f"No subscribers for {symbol} {alert_type}")
            return # Save resources
            
        logger.info(f"Using Dispatcher: Sending {alert_type} on {symbol} to {len(user_ids)} users")
        
        message_html = self._format_message(payload)
        
        async with httpx.AsyncClient() as client:
            for user_id in user_ids:
                try:
                    # Check Per-User Cooldown (e.g. 30 mins per stock)
                    user_cooldown_key = f"cooldown:{user_id}:{symbol}"
                    if await cache.get(user_cooldown_key):
                        continue
                        
                    await self._send_telegram(client, user_id, message_html)
                    
                    # Set Cooldown
                    await cache.set(user_cooldown_key, "1", ttl=1800)
                    
                except Exception as e:
                    logger.error(f"Failed to send to {user_id}: {e}")

    def _format_message(self, payload):
        symbol = payload.get("symbol")
        price = payload.get("price")
        reason = payload.get("reason")
        emoji = "🚀" if "Breakout" in reason or "High" in reason else "🔔"
        
        return (
            f"{emoji} <b>{symbol} Alert</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Price: ₹{price}\n"
            f"Signal: {reason}\n"
            f"Time: {datetime.now().strftime('%H:%M')}\n\n"
            f"<i>Check chart for confirmation.</i>"
        )

    async def _send_telegram(self, client, user_id, text):
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": user_id,
            "text": text,
            "parse_mode": "HTML"
        }
        resp = await client.post(url, json=data, timeout=5.0)
        if resp.status_code != 200:
            logger.error(f"Telegram Send Error {resp.status_code}: {resp.text}")
