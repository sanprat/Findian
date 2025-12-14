import asyncio
import logging
import os
from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.db.models import Alert
import redis
import httpx

logger = logging.getLogger(__name__)

class AlertMonitor:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        # Redis client
        self.redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True)
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.running = False

    async def start(self):
        """Starts the background alert checking loop."""
        self.running = True
        logger.info("🔔 Alert Monitor Started")
        asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self):
        logger.info("🔔 Alert Loop Active")
        while self.running:
            try:
                await self._check_alerts_async()
            except Exception as e:
                logger.error(f"Alert Loop Error: {e}")
            
            # Check every 10 seconds for snappy simulation testing
            await asyncio.sleep(10)

    async def _check_alerts_async(self):
        """Async wrapper to check DB alerts against Redis prices."""
        # Run synchronous DB operations in a thread pool to avoid blocking the loop
        await asyncio.to_thread(self._process_alerts_sync)

    def _process_alerts_sync(self):
        """Synchronous logic to query DB and check conditions."""
        db: Session = SessionLocal()
        try:
            alerts = db.query(Alert).filter(Alert.status == "ACTIVE").all()
            if not alerts:
                return

            for alert in alerts:
                # Get Live Data from Redis
                data = self.redis_client.hgetall(f"stock:{alert.symbol}")
                if not data:
                    continue

                current_value = 0.0
                
                # Extract value
                if alert.indicator.lower() in ["price", "ltp"]:
                    current_value = float(data.get("ltp", 0))
                elif alert.indicator.lower() == "rsi":
                    current_value = float(data.get("rsi", 0))
                
                if current_value == 0: continue

                # Compare
                is_triggered = False
                threshold = float(alert.threshold)
                
                if alert.operator == "gt" and current_value > threshold:
                    is_triggered = True
                elif alert.operator == "lt" and current_value < threshold:
                    is_triggered = True

                if is_triggered:
                    # Send Notification (Fire and Forget)
                    asyncio.run_coroutine_threadsafe(
                        self._trigger_alert(alert, current_value), 
                        asyncio.get_event_loop()
                    )
                    
                    # Mark TRIGGERED in DB
                    alert.status = "TRIGGERED"
                    db.commit()
                    logger.info(f"🚨 Alert Triggered for {alert.symbol}")

        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
        finally:
            db.close()

    async def _trigger_alert(self, alert_obj, current_value: float):
        """Sends notification to Telegram."""
        if not self.bot_token: return

        direction = "above" if alert_obj.operator == "gt" else "below"
        emoji = "🚀" if alert_obj.operator == "gt" else "🔻"
        
        msg = (
            f"🔔 <b>YOUR ALERT TRIGGERED</b>\n\n"
            f"{alert_obj.symbol} crossed {direction} {alert_obj.threshold}\n\n"
            f"📊 <b>Current Data:</b>\n"
            f"• Price: {current_value}\n"
            f"• Indicator: {alert_obj.indicator.upper()}\n\n"
            f"📈 <b>Context:</b>\n"
            f"This matches your criteria of '{alert_obj.indicator} {direction} {alert_obj.threshold}'.\n"
            f"The stock has broken your specified level.\n\n"
            f"⚠️ This is an automated alert based on <b>YOUR</b> settings.\n"
            f"Not investment advice. You decide your next action."
        )

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        async with httpx.AsyncClient() as client:
            try:
                await client.post(url, json={
                    "chat_id": alert_obj.user_id, 
                    "text": msg, 
                    "parse_mode": "HTML"
                })
            except Exception as e:
                logger.error(f"Telegram Send Error: {e}")
