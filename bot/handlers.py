import logging
import os
import aiohttp
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_API_URL", "http://backend:8000")
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")

def get_headers():
    headers = {"Content-Type": "application/json"}
    if API_SECRET_KEY:
        headers["X-API-Key"] = API_SECRET_KEY
    return headers

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /scan [criteria]
    Example: /scan momentum
    """
    query = " ".join(context.args) if context.args else ""
    user_id = update.effective_user.id
    
    if not query:
        await update.message.reply_text("Usage: /scan <criteria>\nExample: /scan breakout")
        return

    msg = await update.message.reply_text(f"🔍 Scanning for: {query}...")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Determine if it's a pre-built type or custom
            endpoint = "/api/screener/custom"
            payload = {"user_id": str(user_id), "query": query}
            
            # Check for keywords to map to pre-built (optional optimization)
            if query.lower() in ["breakout", "volume", "value"]:
                endpoint = f"/api/screener/prebuilt?scan_type=scan_{query.lower()}"
                async with session.get(f"{BACKEND_URL}{endpoint}", headers=get_headers()) as resp:
                     if resp.status == 200:
                         data = await resp.json()
                         # Render results...
                         await msg.edit_text(f"Found {data.get('count')} results for {query}.")
                         return
            
            # Default to Custom AI
            async with session.post(f"{BACKEND_URL}/api/screener/custom", json=payload, headers=get_headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("data", [])
                    
                    if not results:
                        await msg.edit_text(f"No results found for '{query}'.")
                        return
                    
                    text = f"🔍 <b>Results for '{query}'</b>\n\n"
                    for r in results[:10]:
                        text += f"• <b>{r['symbol']}</b>: ₹{r['ltp']}\n"
                    
                    await msg.edit_text(text, parse_mode='HTML')
                else:
                    await msg.edit_text("❌ Scanner Error.")
                    
        except Exception as e:
            logger.error(f"Scan command error: {e}")
            await msg.edit_text("❌ Error executing scan.")

async def alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /alert [condition]
    Example: /alert RELIANCE > 2500
    """
    query = " ".join(context.args)
    user_id = update.effective_user.id
    
    if not query:
        await update.message.reply_text("Usage: /alert <condition>\nExample: /alert TCS > 3000")
        return
        
    # Use existing create alert API
    async with aiohttp.ClientSession() as session:
        try:
            payload = {"user_id": str(user_id), "query": query}
            async with session.post(f"{BACKEND_URL}/api/alert/create", json=payload, headers=get_headers()) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    await update.message.reply_text(res.get("message", "Alert created."))
                else:
                    await update.message.reply_text("❌ Failed to create alert.")
        except Exception as e:
             await update.message.reply_text("❌ Connection Error.")

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /analyze [symbol]
    """
    symbol = context.args[0] if context.args else ""
    if not symbol:
        await update.message.reply_text("Usage: /analyze <SYMBOL>")
        return
        
    # Use quote API + AI
    # For now, just trigger quote
    await update.message.reply_text(f"Analyzing {symbol}... (Feature coming soon)")
