import os
import logging
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove


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
    """Send a welcome message with a Menu."""
    user = update.effective_user
    
    keyboard = [
        ["🔍 Screener", "💼 Portfolio"],
        ["⚠️ Disclaimer"],
        ["🚪 Exit"]
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
        keyboard = [
            ["📋 Pre-built", "🤖 Custom AI"],
            ["💾 Saved Scans", "🔙 Back"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🔍 <b>Market Screener</b>\nFind stocks using technicals or AI:\n\n"
            "• <b>Pre-built:</b> Popular scans (Breakouts, Volume)\n"
            "• <b>Custom AI:</b> Type 'Stocks near support'...\n"
            "• <b>Saved:</b> Run your favorite scans",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
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
        keyboard = [
            ["🔍 Screener", "💼 Portfolio"],
            ["⚠️ Disclaimer"]
        ]
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
        
    # --- SCREENER SUB-COMMANDS ---
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
        await query.message.reply_text("📊 <b>Performance Analysis</b>\nComing soon in next update!", parse_mode='HTML')
        
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

def main():
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN provided!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
