import os
import logging
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton


# ...
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

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
    """Register User and Send Welcome Menu."""
    user = update.effective_user
    
    # Register/Update User in Backend
    async with aiohttp.ClientSession() as session:
        try:
            payload = {
                "telegram_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name
            }
            async with session.post(f"{BACKEND_URL}/api/auth/register", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    is_new = data.get("is_new", False)
                    
                    if is_new:
                         await update.message.reply_text("🆕 <b>Account created successfully!</b>", parse_mode='HTML')
                    else:
                         name = user.first_name if user.first_name else "Trader"
                         await update.message.reply_text(f"👋 Welcome Back <b>{name}</b>!", parse_mode='HTML')

                else:
                    logger.error(f"Registration Failed for {user.id}")
        except Exception as e:
            logger.error(f"Auth Connection Error: {e}")

    keyboard = [
        [KeyboardButton("🔍 Screener"), KeyboardButton("💼 Portfolio")],
        [KeyboardButton("💎 My Plan"), KeyboardButton("📖 Readme")],
        [KeyboardButton("🔒 Privacy Policy")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_html(
        f"Hi {user.mention_html()}! 👋\n\n"
        "I am your <b>AI Financial Assistant</b>.\n"
        "Select a mode below or just type your request!",
        reply_markup=reply_markup
    )

# User States for Conversation Context (MVP memory)
USER_STATES = {}
USER_CONTEXT = {} # Stores temporary data like last_query

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages including Menu buttons and Natural Language."""
    text = update.message.text
    user_id = update.effective_user.id
    current_state = USER_STATES.get(user_id)
    
    # --- STATE HANDLING (Intercept before menu) ---
    if current_state == "WAITING_FOR_SCAN_NAME":
        if text in ["🔙 Back", "🔍 Screener", "start", "/start"] or "Exit" in text:
             USER_STATES.pop(user_id, None)
             await update.message.reply_text("❌ Save cancelled.")
             return
             
        # Save the scan
        last_query = USER_CONTEXT.get(user_id, {}).get("last_query")
        if not last_query:
            await update.message.reply_text("❌ No query found to save.")
            USER_STATES.pop(user_id, None)
            return
            
        async with aiohttp.ClientSession() as session:
            payload = {"user_id": str(user_id), "name": text, "query": last_query}
            async with session.post(f"{BACKEND_URL}/api/screener/save", json=payload) as resp:
                if resp.status == 200:
                    await update.message.reply_text(f"✅ Saved scan as: <b>{text}</b>", parse_mode='HTML')
                else:
                    await update.message.reply_text("❌ Failed to save.")
                    
        USER_STATES.pop(user_id, None)
        return

    if current_state == "WAITING_FOR_SCAN":
        if text in ["🔙 Back", "🔍 Screener", "start", "/start"] or "Exit" in text or "Custom AI" in text:
             # Cancel State
             USER_STATES.pop(user_id, None)
             # Proceed to normal handling below
        else:
            # PROCESS CUSTOM SCAN
            await update.message.reply_text(f"🧠 <b>Analyzing:</b> '{text}'...", parse_mode='HTML')
            
            # Store context
            USER_CONTEXT[user_id] = {"last_query": text}
            
            async with aiohttp.ClientSession() as session:
                try:
                    payload = {"user_id": str(user_id), "query": text}
                    async with session.post(f"{BACKEND_URL}/api/screener/custom", json=payload) as resp:
                        if resp.status == 200:
                            json_data = await resp.json()
                            if not json_data.get("success"):
                                await update.message.reply_text(f"⚠️ {json_data.get('message', 'Unknown Error')}")
                            else:
                                results = json_data.get("data", [])
                                count = json_data.get("count", 0)
                                filters = json_data.get("filters_used", [])
                                
                                # Show Filters Used
                                filter_str = ", ".join([f"{f['field']} {f['op']} {f['value']}" for f in filters])
                                msg = f"🤖 <b>AI Filter:</b> <i>{filter_str}</i>\n\n"
                                
                                msg += f"<b>Results ({count}):</b>\n"
                                msg += f"{'Symbol':<10} {'Price'}\n"
                                msg += "━━━━━━━━━━━━━\n"
                                
                                for r in results[:10]:
                                    msg += f"{r['symbol']:<10} ₹{r['ltp']}\n"
                                    
                                if count > 10: msg += f"<i>...and {count-10} more.</i>"
                                
                                # Add Timestamp and Disclaimer
                                ts = results[0].get("timestamp", "Just now")
                                msg += f"\n\n🕒 Updates: {ts}"
                                msg += "\n\n📊 These stocks match your search filters.\nThis is informational only, not a recommendation."
                                
                                # ADD SAVE BUTTON
                                keyboard = [[InlineKeyboardButton("💾 Save Scan", callback_data="save_scan")]]
                                reply_markup = InlineKeyboardMarkup(keyboard)
                                
                                await update.message.reply_text(f"<pre>{msg}</pre>", parse_mode='HTML', reply_markup=reply_markup)
                        else:
                            await update.message.reply_text("❌ Backend Error.")
                except Exception as e:
                    logger.error(f"Custom Scan Error: {e}")
                    await update.message.reply_text("❌ Error connecting to AI.")
            
            # Reset State
            USER_STATES.pop(user_id, None)
            return

    # --- REUSABLE COMMAND FUNCTIONS ---
    async def show_screener_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            ["📋 Pre-built", "🤖 Custom AI"],
            ["💾 Saved Scans", "🔙 Back"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        # Handle both Message and CallbackQuery contexts if needed (but commands act on messages)
        target = update.message if update.message else update.effective_message
        await target.reply_text(
            "🔍 <b>Market Screener</b>\nFind stocks using technicals or AI:\n\n"
            "• <b>Pre-built:</b> Popular scans (Breakouts, Volume)\n"
            "• <b>Custom AI:</b> Type 'Stocks near support'...\n"
            "• <b>Saved:</b> Run your favorite scans",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    async def show_portfolio_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            ["➕ Add", "✏️ Modify"],
            ["❌ Delete", "👀 View"],
            ["🔙 Back"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        target = update.message if update.message else update.effective_message
        await target.reply_text(
            "💼 <b>Portfolio Management</b>\nSelect an option below:",
            reply_markup=reply_markup
        )

    async def show_plan_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        target = update.message if update.message else update.effective_message
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{BACKEND_URL}/api/subscription/status?user_id={user_id}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        tier = data.get("tier", "FREE")
                        usage = data.get("usage", 0)
                        limit = data.get("limit", 10)
                        
                        # Progress Bar
                        if tier == "ADMIN":
                            bar = "∞" * 10
                            msg = (
                                f"💎 <b>SUBSCRIPTION PLAN</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━\n"
                                f"Plan: <b>{tier}</b>\n"
                                f"Usage: {usage} (Unlimited)\n"
                                f"[∞∞∞∞∞∞∞∞∞∞] 100%\n"
                                f"━━━━━━━━━━━━━━━━━━━\n\n"
                            )
                        else:
                            pct = (usage / limit) * 100 if limit > 0 else 0
                            bar_len = 10
                            filled = int(bar_len * pct / 100)
                            bar = "█" * filled + "░" * (bar_len - filled)
                            
                            msg = (
                                f"💎 <b>SUBSCRIPTION PLAN</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━\n"
                                f"Plan: <b>{tier}</b>\n"
                                f"Usage: {usage}/{limit} requests\n"
                                f"[{bar}] {int(pct)}%\n"
                                f"━━━━━━━━━━━━━━━━━━━\n\n"
                            )
                        
                        keyboard = []
                        if tier == "FREE":
                            msg += "💡 <i>Upgrade to get more daily requests!</i>"
                            keyboard.append([InlineKeyboardButton("✨ Upgrade to PRO (₹199)", callback_data="sub_upgrade_pro")])
                        elif tier == "PRO":
                             msg += "🚀 <i>Need more power? Go Premium!</i>"
                             keyboard.append([InlineKeyboardButton("🔥 Upgrade to PREMIUM (₹499)", callback_data="sub_upgrade_premium")])
                        
                        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")])
                        
                        await target.reply_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
                    else:
                        await target.reply_text("❌ Failed to fetch plan.")
            except Exception as e:
                logger.error(f"Subscription Error: {e}")
                await target.reply_text("❌ Connection Error.")

    # --- MENU HANDLERS ---
    # Intercept Greetings or "start" keyword
    if text.lower() == "start":
        await start(update, context)
        return

    if text.lower() in ["hi", "hello", "hey"]:
        await update.message.reply_text("👋 <b>Welcome!</b>\nPlease type 'start' to activate the AI Financial Assistant.", parse_mode='HTML')
        return

    if "Exit" in text or text.lower() == "exit":
        await update.message.reply_text("👋 <b>Goodbye!</b>\nType 'start' anytime to wake me up.", reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
        return

    if text == "📖 Readme":
        help_text = (
            "📖 <b>Pystock Bot - User Guide</b>\n\n"
            "Here are the commands you can use:\n\n"
            "<b>🔍 Screener</b>\n"
            "• <i>Pre-built:</i> Use menu to find Breakouts/Volume shocks.\n"
            "• <i>Custom AI:</i> Type 'Show stocks with RSI &lt; 30'\n\n"
            "<b>💼 Portfolio</b>\n"
            "• <i>Add:</i> 'Bought 10 TCS at 3000'\n"
            "• <i>Sell:</i> 'Sold 5 TCS at 3200'\n"
            "• <i>View:</i> 'Show my portfolio' or use menu.\n\n"
            "<b>🔔 Alerts</b>\n"
            "• Type: 'Alert me if INFYS &gt; 1500'\n"
            "• Type: 'Alert if NIFTY drops below 18000'\n\n"
            "<b>💎 Subscription</b>\n"
            "• Check 'My Plan' to see your limits.\n"
            "• Admin? Type 'redeem YOUR_CODE' to unlock.\n\n"
            "<i>Just type your request naturally!</i>"
        )
        await update.message.reply_text(help_text, parse_mode='HTML')
        return

    if text == "🔒 Privacy Policy" or text == "/privacy":
        policy_text = (
            "<b>🔒 Privacy Policy</b>\n\n"
            "At Pystock, your privacy and data security are our top priorities.\n\n"
            "✅ <b>No Data Access:</b> We do not access, read, or store your personal portfolio data for any purpose other than providing you with the requested analytics.\n"
            "✅ <b>Local Execution:</b> All critical operations are executed securely on your instance.\n"
            "✅ <b>No Third-Party Sharing:</b> Your data is never shared with, sold to, or used by third parties.\n"
            "✅ <b>Secure Infrastructure:</b> We use industry-standard encryption and security practices to protect your information.\n\n"
            "<i>Your financial data belongs to you, and only you.</i>"
        )
        await update.message.reply_text(policy_text, parse_mode='HTML')
        return

    if text == "⚠️ Disclaimer":
        disclaimer_text = (
            "⚠️ <b>DISCLAIMER</b>\n\n"
            "Findian is a market intelligence and alerting tool.\n\n"
            "We <b>DO NOT</b> provide investment advice or recommendations.\n"
            "We are <b>NOT SEBI registered</b> Investment Advisors or Research Analysts.\n\n"
            "All information is for educational purposes only.\n"
            "Users must conduct their own research and consult with SEBI-registered advisors before making investment decisions.\n\n"
            "Past performance is not indicative of future results.\n"
            "Trading and investing involves risk of loss.\n\n"
            "By using this service, you agree to our Terms of Service."
        )
        await update.message.reply_text(disclaimer_text, parse_mode='HTML')
        return

    if text == "🔔 Alerts":
        await update.message.reply_text("🔔 <b>Alerts Mode</b>\nType: 'Alert me if TCS > 3000'", parse_mode='HTML')
        return

    if text == "🔍 Screener":
        await show_screener_menu(update, context)
        return

    if text == "💼 Portfolio":
        await show_portfolio_menu(update, context)
        return
        
    if "my plan" in text.lower() or text == "💎 My Plan":
        await show_plan_status(update, context)
        return
        
    # --- REDEEM CODE CHECK (Before Main Menu) ---
    if text.lower().startswith("redeem "):
        code = text.split(" ", 1)[1].strip()
        msg = await update.message.reply_text("🔄 Verifying access code...")
        
        async with aiohttp.ClientSession() as session:
            try:
                payload = {"user_id": str(user_id), "code": code}
                async with session.post(f"{BACKEND_URL}/api/subscription/redeem", json=payload) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        if res.get("success"):
                            await msg.edit_text("🎉 <b>Access Granted!</b>\nYou now have Unlimited Admin Access.", parse_mode='HTML')
                        else:
                            await msg.edit_text("❌ Invalid Code.")
                    elif resp.status == 500:
                        await msg.edit_text("❌ Tester mode not configured.")
                    else:
                        await msg.edit_text("❌ Verification failed.")
            except Exception as e:
                logger.error(f"Redeem Error: {e}")
                await msg.edit_text("❌ Connection Error.")
        return

    # --- MAIN MENU ROUTING ---
    if text == "📋 Pre-built":
        # We will show the list of scans here
        # For now, just a placeholder list
        keyboard = [
            [InlineKeyboardButton("📈 Breakout Stocks", callback_data="scan_breakout")],
            [InlineKeyboardButton("🔥 Volume Shockers", callback_data="scan_volume")],
            [InlineKeyboardButton("💎 Value Stocks", callback_data="scan_value")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("📋 <b>Popular Scans</b>\nSelect one to run now:", reply_markup=reply_markup, parse_mode='HTML')
        return

    if "Custom AI" in text:
        USER_STATES[user_id] = "WAITING_FOR_SCAN"
        
        # Mini Disclaimer / Info Block
        info_msg = (
            "🤖 <b>AI Custom Scanner</b>\n"
            "┌─────────────────────────────────────┐\n"
            "│ 📋 <b>Important Information</b>            │\n"
            "│                                     │\n"
            "│ This bot provides alerts and tools  │\n"
            "│ based on <b>YOUR</b> criteria. We don't    │\n"
            "│ advise what to buy or sell.         │\n"
            "│                                     │\n"
            "│ You are responsible for your own    │\n"
            "│ investment decisions.               │\n"
            "└─────────────────────────────────────┘\n\n"
            "I am listening! Type your criteria:\n"
            "Examples:\n• 'RSI &lt; 30 and Price &gt; MA50'\n• 'Stocks near 52W high with volume'"
        )
        await update.message.reply_text(info_msg, parse_mode='HTML')
        return

    if text == "💾 Saved Scans":
        # Fetch Saved Scans
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{BACKEND_URL}/api/screener/saved?user_id={user_id}") as resp:
                    if resp.status == 200:
                        json_data = await resp.json()
                        scans = json_data.get("data", [])
                        
                        if not scans:
                            await update.message.reply_text("💾 <b>Saved Scans</b>\n\nYou haven't saved any scans yet.\nTry running a custom scan and clicking 'Save'!", parse_mode='HTML')
                        else:
                            keyboard = []
                            for s in scans:
                                # Row with [Run Name] [Delete]
                                # Note: Delete might be risky to put right next to it without confirmation, but for MVP ok.
                                # Or just list them to Run.
                                keyboard.append([
                                    InlineKeyboardButton(f"🚀 {s['name']}", callback_data=f"saved_run_{s['id']}"),
                                    InlineKeyboardButton("❌", callback_data=f"saved_del_{s['id']}")
                                ])
                            
                            keyboard.append([InlineKeyboardButton("🔙 Back to Screener", callback_data="back_to_screener")])
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            
                            await update.message.reply_text("💾 <b>Your Saved Scans</b>\nSelect to Run:", reply_markup=reply_markup, parse_mode='HTML')
                    else:
                        await update.message.reply_text("❌ Error fetching saved scans.")
            except Exception as e:
                logger.error(f"Saved Scans Error: {e}")
                await update.message.reply_text("❌ Connection Error.")
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
        intent = result.get("intent")

        
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

        elif intent == "VIEW_PORTFOLIO":
            # Fetch and display portfolio
            await status_msg.edit_text("🔄 Fetching Portfolio...")
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BACKEND_URL}/api/portfolio/list?user_id={user_id}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        holdings = data.get("holdings", [])
                        summary = data.get("summary", {})
                        
                        if not holdings:
                            await status_msg.edit_text("💼 Your portfolio is empty.")
                        else:
                            # 1. HEADER
                            total_val = summary.get('total_value', 0)
                            total_pnl = summary.get('total_pnl', 0)
                            total_pct = summary.get('total_pnl_percent', 0)
                            
                            pnl_emoji = "💰" if total_pnl >= 0 else "📉"
                            sign = "+" if total_pnl >= 0 else ""
                            
                            msg = "📊 <b>Your Portfolio</b>\n"
                            msg += f"Total Value: ₹{total_val:,.2f}\n"
                            msg += f"Total P&L: {sign}₹{total_pnl:,.2f} ({sign}{total_pct:,.2f}%) {pnl_emoji}\n"
                            msg += "━━━━━━━━━━━━━━━━━━━\n\n"
                            
                            # 2. HOLDINGS LIST
                            for h in holdings:
                                sym = h['symbol']
                                qty = h['quantity']
                                avg = h['avg_price']
                                ltp = h['ltp']
                                pnl = h['pnl']
                                pnl_pct = h['pnl_percent']
                                val = h['current_value']
                                
                                row_emoji = "📈" if pnl >= 0 else "📉"
                                row_sign = "+" if pnl >= 0 else ""
                                
                                msg += f"<b>{sym}</b> | {qty} shares\n"
                                msg += f"Buy: ₹{avg:,.2f} → Now: ₹{ltp:,.2f}\n"
                                msg += f"P&L: {row_sign}₹{pnl:,.2f} ({row_sign}{pnl_pct:,.2f}%) {row_emoji}\n"
                                msg += f"Value: ₹{val:,.2f}\n\n"
                            
                            msg += "━━━━━━━━━━━━━━━━━━━\n"
                            msg += "Last updated: Just now"

                            # 3. INLINE BUTTONS
                            keyboard = [
                                [
                                    InlineKeyboardButton("Details", callback_data="p_details"),
                                    InlineKeyboardButton("Performance", callback_data="p_perf"),
                                    InlineKeyboardButton("Add Position", callback_data="p_add")
                                ]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            
                            await status_msg.edit_text(msg, parse_mode='HTML', reply_markup=reply_markup)
                    else:
                         await status_msg.edit_text("❌ Failed to fetch portfolio.")

        elif intent == "CHECK_PRICE":
            symbol = result.get("data", {}).get("symbol")
            if not symbol:
                await status_msg.edit_text("❓ Which stock?")
            else:
                async with aiohttp.ClientSession() as session:
                     async with session.get(f"{BACKEND_URL}/api/quote/{symbol}") as resp:
                         if resp.status == 200:
                             json_res = await resp.json()
                             if json_res.get("success"):
                                 q = json_res['data']
                                 
                                 emoji = "🚀" if q['ltp'] >= q['close'] else "🔻"
                                 color = "🟢" if q['ltp'] >= q['close'] else "🔴"
                                 diff = q['ltp'] - q['close']
                                 pct = (diff / q['close']) * 100 if q['close'] > 0 else 0
                                 
                                 msg = (
                                     f"{emoji} <b>{q['symbol']}</b>\n"
                                     f"━━━━━━━━━━━━━━━━━━━\n"
                                     f"Price: <b>₹{q['ltp']:,.2f}</b>\n"
                                     f"Change: {color} {diff:+.2f} ({pct:+.2f}%)\n"
                                     f"Vol: {q['volume']:,}\n"
                                     f"H/L: {q['high']:,.2f} / {q['low']:,.2f}\n"
                                     f"━━━━━━━━━━━━━━━━━━━\n"
                                     f"🕒 Live Quote"
                                 )
                                 
                                 # Action Buttons
                                 # (Add to Portfolio needs a specific handler, keeping it simple for now)
                                 # keyboard = [[InlineKeyboardButton("➕ Add to Portfolio", callback_data=f"p_add_auto_{q['symbol']}")]]
                                 await status_msg.edit_text(msg, parse_mode='HTML')
                             else:
                                 await status_msg.edit_text(f"❌ Could not find quote for {symbol}.")
                         else:
                             await status_msg.edit_text("❌ Quote Service Error.")

        elif status == "ERROR":
            await status_msg.edit_text(f"❌ {result.get('message', 'An error occurred.')}")

        else:
            await status_msg.edit_text("⚠️ Unknown Response.")

    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text("❌ System Error.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer() # Acknowledge interaction
    
    data = query.data
    user_id = update.effective_user.id
    
    if data == "p_add":
        await query.message.reply_text("📝 <b>Add Holding</b>\nType: 'Bought 10 TCS at 3000'", parse_mode='HTML')
    
    elif data == "save_scan":
        # Check if we have context
        last_query = USER_CONTEXT.get(user_id, {}).get("last_query")
        if not last_query:
            await query.answer("No scan to save!", show_alert=True)
            return
            
        USER_STATES[user_id] = "WAITING_FOR_SCAN_NAME"
        await query.message.reply_text("💾 <b>Name your Scan:</b>\nType a name (e.g., 'Oversold RSI')", parse_mode='HTML')
        
    elif data.startswith("saved_run_"):
        # Run a saved scan
        scan_id = data.split("_")[2]
        scan_name = data.split("_")[3] if len(data.split("_")) > 3 else "Scan"
        
        # We need the query text. Ideally we should have fetched it.
        # But wait, to run it, we need the *text*.
        # Let's fetch the specific scan or list again?
        # Optimization: We can just trigger the custom scan logic passed as argument? No, too long for callback data.
        # We must fetch the query from backend by ID? Or just list all and find it.
        # Let's simple Fetch-All and Find.
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/screener/saved?user_id={user_id}") as resp:
                if resp.status == 200:
                    json_data = await resp.json()
                    scans = json_data.get("data", [])
                    target = next((s for s in scans if str(s['id']) == scan_id), None)
                    
                    if target:
                        query_text = target['query']
                        await query.message.reply_text(f"🚀 Running saved scan: <b>{target['name']}</b>", parse_mode='HTML')
                        # Trigger existing Custom AI logic by simulated text?
                        # No, just reuse code or call API directly. Direct API call is cleaner.
                        
                        payload = {"user_id": str(user_id), "query": query_text}
                        async with session.post(f"{BACKEND_URL}/api/screener/custom", json=payload) as scan_resp:
                             # ... Same result rendering logic as Custom AI ...
                             if scan_resp.status == 200:
                                 r_json = await scan_resp.json()
                                 results = r_json.get("data", [])
                                 count = r_json.get("count", 0)
                                 
                                 msg = f"🔍 <b>Results for '{target['name']}':</b>\n\n"
                                 msg += f"{'Symbol':<10} {'Price'}\n━━━━━━━━━━━━━\n"
                                 for r in results[:10]:
                                     msg += f"{r['symbol']:<10} ₹{r['ltp']}\n"
                                 if count > 10: msg += f"<i>...and {count-10} more.</i>"
                                 
                                 await query.message.reply_text(f"<pre>{msg}</pre>", parse_mode='HTML')
                             else:
                                 await query.message.reply_text("❌ Scan failed.")
                    else:
                        await query.message.reply_text("❌ Scan not found.")
                        
    elif data.startswith("saved_del_"):
        scan_id = data.split("_")[2]
        async with aiohttp.ClientSession() as session:
             async with session.delete(f"{BACKEND_URL}/api/screener/saved/{scan_id}?user_id={user_id}") as resp:
                 if resp.status == 200:
                     await query.answer("Scan Deleted!", show_alert=True)
                     # Refresh list? Ideally yes, but for now just acknowledge.
                     await query.message.delete() # Remove button list
                     await query.message.reply_text("🗑️ Scan Deleted.")
                 else:
                     await query.answer("Delete Failed", show_alert=True)

    elif data == "p_perf":
        await query.edit_message_text("📊 Generating Performance Chart... Please wait.")
        
        async with aiohttp.ClientSession() as session:
            try:
                # Fetch Data
                async with session.get(f"{BACKEND_URL}/api/portfolio/performance?user_id={user_id}") as resp:
                    if resp.status == 200:
                        json_data = await resp.json()
                        dates = json_data.get("dates", [])
                        values = json_data.get("values", [])
                        
                        if not dates or len(dates) < 2:
                            await query.message.reply_text("📉 Not enough data for a chart yet.")
                            return

                        # Generate Chart
                        import matplotlib.pyplot as plt
                        import pandas as pd
                        import io
                        
                        # Data Prep
                        df = pd.DataFrame({'Date': pd.to_datetime(dates), 'Value': values})
                        
                        plt.figure(figsize=(10, 5))
                        plt.plot(df['Date'], df['Value'], marker='o', linestyle='-', color='#007bff', linewidth=2, markersize=4)
                        
                        plt.title("Portfolio Equity Curve (30 Days)", fontsize=14, fontweight='bold')
                        plt.xlabel("Date", fontsize=10)
                        plt.ylabel("Value (₹)", fontsize=10)
                        plt.grid(True, linestyle='--', alpha=0.6)
                        plt.xticks(rotation=45)
                        plt.tight_layout()
                        
                        # Save to Buffer
                        buf = io.BytesIO()
                        plt.savefig(buf, format='png')
                        buf.seek(0)
                        plt.close()
                        
                        # Calculate Change
                        start_val = values[0]
                        end_val = values[-1]
                        change = end_val - start_val
                        pct = (change / start_val) * 100 if start_val > 0 else 0
                        emoji = "🚀" if change >= 0 else "🔻"
                        sign = "+" if change >= 0 else ""
                        
                        caption = (
                            f"📊 <b>Portfolio Performance</b>\n"
                            f"30-Day Change: {sign}₹{change:,.2f} ({sign}{pct:.2f}%) {emoji}\n"
                            f"Current Value: ₹{end_val:,.2f}"
                        )
                        
                        # Send Photo (Delete loading text first)
                        await query.message.delete()
                        await query.message.reply_photo(photo=buf, caption=caption, parse_mode='HTML')
                        
                        # Re-show menu?
                        # await show_portfolio_menu... (Optional, but let's keep it clean)
                        
                    else:
                        await query.message.reply_text("❌ Failed to fetch performance data.")
            except Exception as e:
                logger.error(f"Chart Error: {e}")
                await query.message.reply_text("❌ Error generating chart.")
        
    elif data == "p_details":
        # Fetch symbols to show selection
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/portfolio/list?user_id={user_id}") as resp:
                if resp.status == 200:
                    json_data = await resp.json()
                    holdings = json_data.get("holdings", [])
                    
                    if not holdings:
                        await query.edit_message_text("Portfolio is empty.")
                        return

                    # Create buttons for each stock
                    keyboard = []
                    for h in holdings:
                        sym = h['symbol']
                        keyboard.append([InlineKeyboardButton(f"📊 {sym}", callback_data=f"stock_{sym}")])
                    
                    keyboard.append([InlineKeyboardButton("🔙 Back to Overview", callback_data="p_overview")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text("Select stock for details:", reply_markup=reply_markup)
                else:
                    await query.message.reply_text("❌ Error fetching data.")

    elif data == "p_overview":
         # Re-trigger view logic (simplified by calling backend again or just static text if cache existed, but backend call is safer)
         # For MVP, we just say "Type 'Show Portfolio'" or re-render (requires refactoring view logic to valid function). 
         # For now, let's just send a fresh message or try to edit back.
         # Ideally we should refactor 'show_portfolio_render' function. 
         # I will just trigger the text handler logic via a trick or duplicate the render logic.
         # Duplicating logic for safety in this single-file edit:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BACKEND_URL}/api/portfolio/list?user_id={user_id}") as resp:
                    if resp.status == 200:
                        json_data = await resp.json()
                        holdings = json_data.get("holdings", [])
                        summary = json_data.get("summary", {})
                        
                        # 1. HEADER
                        total_val = summary.get('total_value', 0)
                        total_pnl = summary.get('total_pnl', 0)
                        total_pct = summary.get('total_pnl_percent', 0)
                        
                        pnl_emoji = "💰" if total_pnl >= 0 else "📉"
                        sign = "+" if total_pnl >= 0 else ""
                        
                        msg = f"📊 <b>Your Portfolio</b>\n"
                        msg += f"Total Value: ₹{total_val:,.2f}\n"
                        msg += f"Total P&L: {sign}₹{total_pnl:,.2f} ({sign}{total_pct:,.2f}%) {pnl_emoji}\n"
                        msg += "━━━━━━━━━━━━━━━━━━━\n\n"
                        
                        # 2. HOLDINGS LIST
                        for h in holdings:
                            sym = h['symbol']
                            qty = h['quantity']
                            avg = h['avg_price']
                            ltp = h['ltp']
                            pnl = h['pnl']
                            pnl_pct = h['pnl_percent']
                            val = h['current_value']
                            
                            row_emoji = "📈" if pnl >= 0 else "📉"
                            row_sign = "+" if pnl >= 0 else ""
                            
                            msg += f"<b>{sym}</b> | {qty} shares\n"
                            msg += f"Buy: ₹{avg:,.2f} → Now: ₹{ltp:,.2f}\n"
                            msg += f"P&L: {row_sign}₹{pnl:,.2f} ({row_sign}{pnl_pct:,.2f}%) {row_emoji}\n"
                            msg += f"Value: ₹{val:,.2f}\n\n"
                        
                        msg += "━━━━━━━━━━━━━━━━━━━\n"
                        msg += "Last updated: Just now"
                        
                        # Re-attach Main Buttons
                        keyboard = [[
                            InlineKeyboardButton("Details", callback_data="p_details"),
                            InlineKeyboardButton("Performance", callback_data="p_perf"),
                            InlineKeyboardButton("Add Position", callback_data="p_add")
                        ]]
                        await query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
                    else:
                        await query.edit_message_text("❌ Error fetching portfolio overview.")




    # --- SCREENER HANDLING ---
    elif data.startswith("scan_"):
        # scan_breakout, scan_volume...
        scan_type = data
        scan_title = data.replace("scan_", "").title()
        
        await query.edit_message_text(f"🔄 Running {scan_title} Scan...")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{BACKEND_URL}/api/screener/prebuilt?scan_type={scan_type}") as resp:
                    if resp.status == 200:
                        json_data = await resp.json()
                        results = json_data.get("data", [])
                        count = json_data.get("count", 0)
                        
                        if not results:
                            await query.edit_message_text(f"🔍 <b>{scan_title} Scan</b>\n\nNo matches found right now.", parse_mode='HTML')
                            return
                        
                        # Format Results
                        msg = f"🔍 <b>{scan_title} Results ({count})</b>\n\n"
                        msg += f"{'Symbol':<10} {'Price':<8} {'%Chg':<6}\n"
                        msg += "━━━━━━━━━━━━━━━━━━━\n"
                        
                        # Show top 10
                        for r in results[:10]:
                            emoji = "🚀" if r['change_percent'] > 0 else "🔻"
                            msg += f"{r['symbol']:<10} {r['ltp']:<8} {r['change_percent']:<6}% {emoji}\n"
                            
                        if count > 10:
                            msg += f"\n<i>...and {count-10} more.</i>"
                        
                        # Add Timestamp and Disclaimer
                        ts = results[0].get("timestamp", "Just now")
                        msg += f"\n\n🕒 Updates: {ts}"
                        msg += "\n\n📊 These stocks match technical filters.\nThis is informational only, not a recommendation."

                        # Add Action Buttons (could be Save Scan in future)
                        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_screener")]]
                        await query.edit_message_text(f"<pre>{msg}</pre>", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
                    else:
                        await query.edit_message_text("❌ Scanner Service Unavailable.")
            except Exception as e:
                logger.error(f"Bot Scanner Error: {e}")
                await query.edit_message_text("❌ Error connecting to Scanner.")

    elif data == "back_to_screener":
        # Show Screener Menu again
        keyboard = [
            [InlineKeyboardButton("📈 Breakout Stocks", callback_data="scan_breakout")],
            [InlineKeyboardButton("🔥 Volume Shockers", callback_data="scan_volume")],
            [InlineKeyboardButton("💎 Value Stocks", callback_data="scan_value")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📋 <b>Popular Scans</b>\nSelect one to run now:", reply_markup=reply_markup, parse_mode='HTML')

    elif data.startswith("stock_"):
        symbol = data.split("_")[1]
        
        # Fetch specific details
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/portfolio/list?user_id={user_id}") as resp:
                if resp.status == 200:
                    json_data = await resp.json()
                    holdings = json_data.get("holdings", [])
                    
                    # Find specific holding
                    target = next((h for h in holdings if h["symbol"] == symbol), None)
                    
                    if target:
                        # RENDER DETAILED CARD
                        # Fields: symbol, quantity, avg_price, ltp, current_value, pnl, pnl_percent, invested, day_change, day_change_percent, day_pnl, high, low
                        
                        pnl_sign = "+" if target['pnl'] >= 0 else ""
                        day_sign = "+" if target['day_change'] >= 0 else ""
                        
                        msg = f"📊 <b>{symbol} - Detailed View</b>\n\n"
                        msg += "<b>Position:</b>\n"
                        msg += f"• Quantity: {target['quantity']}\n"
                        msg += f"• Avg Buy: ₹{target['avg_price']:,.2f}\n"
                        msg += f"• Current: ₹{target['ltp']:,.2f} ({day_sign}{target['day_change_percent']}%) {day_sign}₹{target['day_change']}\n"
                        msg += f"• Invested: ₹{target['invested']:,.2f}\n"
                        msg += f"• Value: ₹{target['current_value']:,.2f}\n"
                        msg += f"• Unrealized P&L: {pnl_sign}₹{target['pnl']:,.2f} ({pnl_sign}{target['pnl_percent']}%) 💰\n\n"
                        
                        msg += "<b>Today's Session:</b>\n"
                        msg += f"• High: ₹{target['high']:,.2f}\n"
                        msg += f"• Low: ₹{target['low']:,.2f}\n"
                        msg += f"• Day P&L: {day_sign}₹{target['day_pnl']:,.2f}\n"

                        keyboard = [[InlineKeyboardButton("🔙 Back to List", callback_data="p_details")]]
                        await query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
                    else:
                        await query.edit_message_text("❌ Stock not found.")

    
    elif data.startswith("sub_upgrade_"):
        # Payment Integration Pending
        await query.answer("🚧 Payments Coming Soon!", show_alert=True)
        await query.message.edit_text(
            "🚧 <b>Coming Soon!</b>\n\n"
            "We are currently integrating a secure payment gateway (Razorpay).\n"
            "Stay tuned for updates!",
            parse_mode='HTML'
        )

    elif data == "back_to_menu":
        await query.message.delete()
        # Clean exit to menu logic or just let user type command

def main():
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN provided!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # on different commands - answer in Telegram
    
    # WEBHOOK MODE (For Production)
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.getenv("PORT", "8443"))
    
    
    # Define commands list
    async def post_init(application: Application):
        from telegram import BotCommand
        await application.bot.set_my_commands([
            BotCommand("start", "Restart Bot & Menu"),
            BotCommand("plan", "💎 My Subscription Plan"),
            BotCommand("screener", "🔍 Stock Screener"),
            BotCommand("portfolio", "💼 My Portfolio"),
            BotCommand("help", "❓ Help & Usage")
        ])

    # Define Command Aliases (Shared for both modes)
    # NOTE: Command handlers must accept (update, context)
    async def cmd_plan_alias(u, c): 
        await show_plan_status(u, c)

    async def cmd_screen_alias(u, c): 
        await show_screener_menu(u, c)

    async def cmd_port_alias(u, c): 
        await show_portfolio_menu(u, c)

    async def cmd_help_alias(u, c):
        await u.message.reply_text("Type 'start' for menu.")

    if WEBHOOK_URL:
        logger.info(f"🚀 Starting Bot in WEBHOOK mode on port {PORT}")
        # Attach post_init
        application.post_init = post_init
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("plan", cmd_plan_alias))
        application.add_handler(CommandHandler("screener", cmd_screen_alias))
        application.add_handler(CommandHandler("portfolio", cmd_port_alias))
        application.add_handler(CommandHandler("help", cmd_help_alias))
        
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
    else:
        # POLLING MODE (For Development)
        logger.info("🚀 Starting Bot in POLLING mode")
        
        application.post_init = post_init
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("plan", cmd_plan_alias))
        application.add_handler(CommandHandler("screener", cmd_screen_alias))
        application.add_handler(CommandHandler("portfolio", cmd_port_alias))
        application.add_handler(CommandHandler("help", cmd_help_alias))

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        application.run_polling()

if __name__ == "__main__":
    main()
