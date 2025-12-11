import os
import logging
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_API_URL", "http://backend:8000")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message with a Menu."""
    user = update.effective_user
    
    keyboard = [
        ["🔔 Alerts", "💼 Portfolio"],
        ["❓ Help"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_html(
        f"Hi {user.mention_html()}! 👋\n\n"
        "I am your <b>AI Financial Assistant</b>.\n"
        "Select a mode below or just type your request!",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages including Menu buttons and Natural Language."""
    text = update.message.text
    user_id = update.effective_user.id
    
    # --- MENU HANDLERS ---
    if text == "🔔 Alerts":
        await update.message.reply_text("🔔 <b>Alerts Mode</b>\nType: 'Alert me if TCS > 3000'", parse_mode='HTML')
        return

    if text == "💼 Portfolio":
        # Show Sub-Menu
        keyboard = [
            ["➕ Add", "✏️ Modify"],
            ["❌ Delete", "👀 View"],
            ["🔙 Back"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "💼 <b>Portfolio Management</b>\nSelect an option below:",
            reply_markup=reply_markup
        )
        return

    if text == "🔙 Back":
        # Return to Main Menu
        keyboard = [["🔔 Alerts", "💼 Portfolio"], ["❓ Help"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("🏠 Main Menu", reply_markup=reply_markup)
        return

    # --- PORTFOLIO SUB-COMMANDS (Instructions) ---
    if text == "➕ Add":
        await update.message.reply_text("📝 <b>Add Holding</b>\nType: 'Bought 10 TCS at 3000'", parse_mode='HTML')
        return
    
    if text == "✏️ Modify":
        await update.message.reply_text("✏️ <b>Modify Holding</b>\nType: 'Update TCS quantity to 20'", parse_mode='HTML')
        return

    if text == "❌ Delete":
        await update.message.reply_text("🗑️ <b>Delete Holding</b>\nType: 'Delete TCS from portfolio'", parse_mode='HTML')
        return
        
    if text == "👀 View":
        # Trigger View Logic directly
        text = "Show my portfolio" 
        # Fallthrough to AI logic below with this text

    if text == "❓ Help":
        await update.message.reply_text("Try: 'Alert if RELIANCE > 2500' or 'Bought 50 INFY at 1400'")
        return

    # --- AI PROCESSING ---
    status_msg = await update.message.reply_text("🤔 Analysing...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/api/alert/create",
                json={"user_id": str(user_id), "query": text}
            ) as response:
                if response.status != 200:
                    await status_msg.edit_text("❌ Error connecting to backend.")
                    return
                
                result = await response.json()
        
        # --- HANDLE SCENARIOS ---
        status = result.get("status")
        
        if status == "NEEDS_CLARIFICATION":
            await status_msg.edit_text(f"❓ {result.get('question')}")
            
        elif status == "REJECTED":
            await status_msg.edit_text(f"🛑 {result.get('message')}")

        elif status == "CREATED":
            await status_msg.edit_text(result.get("message"))

        elif status == "PORTFOLIO_ADDED":
            await status_msg.edit_text(result.get("message"))
   
        elif status == "PORTFOLIO_DELETED":
            await status_msg.edit_text(result.get("message"))

        elif status == "PORTFOLIO_UPDATED":
            await status_msg.edit_text(result.get("message"))

        elif status == "VIEW_PORTFOLIO_REQ":
            # Fetch and display portfolio
            await status_msg.edit_text("🔄 Fetching Portfolio...")
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BACKEND_URL}/api/portfolio/list?user_id={user_id}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        holdings = data.get("holdings", [])
                        if not holdings:
                            await status_msg.edit_text("💼 Your portfolio is empty.")
                        else:
                            # Format Table
                            msg = "<b>💼 Your Portfolio</b>\n\n"
                            msg += f"{'Symbol':<10} {'Qty':<5} {'Avg':<8}\n"
                            msg += "-"*30 + "\n"
                            for h in holdings:
                                msg += f"{h['symbol']:<10} {h['quantity']:<5} {h['avg_price']:<8}\n"
                            
                            await status_msg.edit_text(f"<pre>{msg}</pre>", parse_mode='HTML')
                    else:
                         await status_msg.edit_text("❌ Failed to fetch portfolio.")

        else:
            await status_msg.edit_text("⚠️ Unknown Response.")

    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text("❌ System Error.")

def main():
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN provided!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
