import os
import logging
import aiohttp
import html  # SECURITY: For escaping user input in HTML output
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
)


# ...
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
from handlers import scan_command, alert_command, analyze_command

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_API_URL", "http://backend:8000")
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")


def get_api_headers():
    """
    SECURITY: Returns headers including the API key for authenticated requests.
    """
    headers = {"Content-Type": "application/json"}
    if API_SECRET_KEY:
        headers["X-API-Key"] = API_SECRET_KEY
    return headers


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register User and Send Welcome Menu."""
    user = update.effective_user

    # Show keyboard immediately (don't wait for backend)
    keyboard = [
        [KeyboardButton("🔍 Screener"), KeyboardButton("💼 Portfolio")],
        [KeyboardButton("📊 Stock Tools"), KeyboardButton("💎 My Plan")],
        [KeyboardButton("📖 Readme"), KeyboardButton("📞 Contact Support")],
        [KeyboardButton("🔒 Privacy Policy")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_html(
        f"Hi {user.mention_html()}! 👋\n\n"
        "I am your <b>AI Financial Assistant</b>.\n"
        "Select a mode below or just type your request!",
        reply_markup=reply_markup,
    )

    # Register user in background (with timeout)
    try:
        timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            payload = {
                "telegram_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
            async with session.post(
                f"{BACKEND_URL}/api/auth/register",
                json=payload,
                headers=get_api_headers(),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    is_new = data.get("is_new", False)
                    if is_new:
                        await update.message.reply_text(
                            "🆕 <b>Account created!</b>", parse_mode="HTML"
                        )
    except Exception as e:
        logger.warning(f"Backend registration skipped: {e}")


# User States for Conversation Context (MVP memory)
USER_STATES = {}
USER_CONTEXT = {}  # Stores temporary data like last_query


# --- REUSABLE COMMAND FUNCTIONS (Module Level) ---
async def show_screener_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the Screener menu."""
    keyboard = [["📋 Pre-built", "🤖 Custom AI"], ["💾 Saved Scans", "🏠 Main Menu"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    target = update.message if update.message else update.effective_message
    await target.reply_text(
        "🔍 <b>Market Screener</b>\nFind stocks using technicals or AI:\n\n"
        "• <b>Pre-built:</b> Popular scans (Breakouts, Volume)\n"
        "• <b>Custom AI:</b> Type 'Stocks near support'...\n"
        "• <b>Saved:</b> Run your favorite scans",
        reply_markup=reply_markup,
        parse_mode="HTML",
    )


async def show_portfolio_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the Portfolio menu."""
    keyboard = [["➕ Add", "✏️ Modify"], ["❌ Delete", "👀 View"], ["🏠 Main Menu"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    target = update.message if update.message else update.effective_message
    await target.reply_text(
        "💼 <b>Portfolio Management</b>\nSelect an option below:",
        reply_markup=reply_markup,
        parse_mode="HTML",
    )


async def show_plan_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display subscription plan status."""
    user_id = update.effective_user.id
    target = update.message if update.message else update.effective_message

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{BACKEND_URL}/api/subscription/status?user_id={user_id}",
                headers=get_api_headers(),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tier = data.get("tier", "FREE")
                    usage = data.get("usage", 0)
                    limit = data.get("limit", 10)

                    # Progress Bar
                    if tier == "ADMIN":
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
                        keyboard.append(
                            [
                                InlineKeyboardButton(
                                    "✨ Upgrade to PRO (₹199)",
                                    callback_data="sub_upgrade_pro",
                                )
                            ]
                        )
                    elif tier == "PRO":
                        msg += "🚀 <i>Need more power? Go Premium!</i>"
                        keyboard.append(
                            [
                                InlineKeyboardButton(
                                    "🔥 Upgrade to PREMIUM (₹499)",
                                    callback_data="sub_upgrade_premium",
                                )
                            ]
                        )

                    keyboard.append(
                        [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
                    )

                    await target.reply_text(
                        msg,
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )
                else:
                    await target.reply_text("❌ Failed to fetch plan.")
        except Exception as e:
            logger.error(f"Subscription Error: {e}")
            await target.reply_text("❌ Connection Error.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages including Menu buttons and Natural Language."""
    text = update.message.text
    user_id = update.effective_user.id
    current_state = USER_STATES.get(user_id)

    # --- STATE HANDLING (Intercept before menu) ---
    if current_state == "WAITING_FOR_SCAN_NAME":
        if (
            text
            in [
                "🔙 Back",
                "🏠 Main Menu",
                "Main Menu",
                "Back",
                "🔍 Screener",
                "start",
                "/start",
            ]
            or "Exit" in text
        ):
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
            async with session.post(
                f"{BACKEND_URL}/api/screener/save",
                json=payload,
                headers=get_api_headers(),
            ) as resp:
                if resp.status == 200:
                    await update.message.reply_text(
                        f"✅ Saved scan as: <b>{text}</b>", parse_mode="HTML"
                    )
                else:
                    await update.message.reply_text("❌ Failed to save.")

        USER_STATES.pop(user_id, None)
        return

    # --- SUPPORT STATE HANDLERS ---
    if current_state in ["WAITING_FOR_ISSUE", "WAITING_FOR_FEEDBACK"]:
        if text.lower() in ["back", "cancel", "exit", "main menu", "🏠 main menu"]:
            USER_STATES.pop(user_id, None)
            await start(update, context)
            return
        
        category = "ISSUE" if current_state == "WAITING_FOR_ISSUE" else "FEEDBACK"
        
        async with aiohttp.ClientSession() as session:
            try:
                payload = {
                    "user_id": str(user_id),
                    "category": category,
                    "message": text
                }
                async with session.post(
                    f"{BACKEND_URL}/api/support/submit",
                    json=payload,
                    headers=get_api_headers(),
                ) as resp:
                    if resp.status == 200:
                        await update.message.reply_text(
                            f"✅ <b>{category.title()} Submitted!</b>\nThank you for reaching out. We will review it shortly.", 
                            parse_mode="HTML"
                        )
                    else:
                        await update.message.reply_text("❌ Failed to submit. Please try again later.")
            except Exception as e:
                logger.error(f"Support Submit Error: {e}")
                await update.message.reply_text("❌ Connection Error.")
        
        USER_STATES.pop(user_id, None)
        await start(update, context)
        return

    if current_state == "WAITING_FOR_SCAN":
        if (
            text
            in [
                "🔙 Back",
                "🏠 Main Menu",
                "Main Menu",
                "Back",
                "🔍 Screener",
                "start",
                "/start",
            ]
            or "Exit" in text
            or "Custom AI" in text
        ):
            # Cancel State
            USER_STATES.pop(user_id, None)
            # Proceed to normal handling below
        else:
            # PROCESS CUSTOM SCAN
            await update.message.reply_text(
                f"🧠 <b>Analyzing:</b> '{text}'...", parse_mode="HTML"
            )

            # Store context
            USER_CONTEXT[user_id] = {"last_query": text}

            async with aiohttp.ClientSession() as session:
                try:
                    payload = {"user_id": str(user_id), "query": text}
                    async with session.post(
                        f"{BACKEND_URL}/api/screener/custom",
                        json=payload,
                        headers=get_api_headers(),
                    ) as resp:
                        if resp.status == 200:
                            json_data = await resp.json()
                            if not json_data.get("success"):
                                await update.message.reply_text(
                                    f"⚠️ {json_data.get('message', 'Unknown Error')}"
                                )
                            else:
                                results = json_data.get("data", [])
                                count = json_data.get("count", 0)
                                filters = json_data.get("filters_used", [])

                                # Show Filters Used
                                filter_str = ", ".join(
                                    [
                                        f"{f['field']} {f['op']} {f['value']}"
                                        for f in filters
                                    ]
                                )
                                msg = f"🤖 <b>AI Filter:</b> <i>{filter_str}</i>\n\n"

                                msg += f"<b>Results ({count}):</b>\n"
                                msg += f"{'Symbol':<10} {'Price'}\n"
                                msg += "━━━━━━━━━━━━━\n"

                                for r in results[:10]:
                                    msg += f"{r['symbol']:<10} ₹{r['ltp']}\n"

                                if count > 10:
                                    msg += f"<i>...and {count - 10} more.</i>"

                                # Add Timestamp and Disclaimer
                                ts = results[0].get("timestamp", "Just now")
                                msg += f"\n\n🕒 Updates: {ts}"
                                msg += "\n\n📊 These stocks match your search filters.\nThis is informational only, not a recommendation."

                                # ADD SAVE BUTTON
                                keyboard = [
                                    [
                                        InlineKeyboardButton(
                                            "💾 Save Scan", callback_data="save_scan"
                                        )
                                    ]
                                ]
                                reply_markup = InlineKeyboardMarkup(keyboard)

                                await update.message.reply_text(
                                    f"<pre>{msg}</pre>",
                                    parse_mode="HTML",
                                    reply_markup=reply_markup,
                                )
                        else:
                            await update.message.reply_text("❌ Backend Error.")
                except Exception as e:
                    logger.error(f"Custom Scan Error: {e}")
                    await update.message.reply_text("❌ Error connecting to AI.")

            # Reset State
            USER_STATES.pop(user_id, None)
            return

    # --- STOCK TOOLS STATE HANDLERS ---
    if current_state == "WAITING_FOR_CHART_SYMBOL":
        if text.lower() in ["back", "cancel", "exit", "main menu"]:
            USER_STATES.pop(user_id, None)
            await update.message.reply_text("❌ Cancelled.")
            await start(update, context)
            return
        
        symbol = text.upper()
        # KEEP STATE: USER_STATES.pop(user_id, None)
        status_msg = await update.message.reply_text(f"📊 Generating chart for {symbol}...\n(Type another symbol or 'Back' to exit)")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/chart/{symbol}", headers=get_api_headers()) as resp:
                chart_data = await resp.json()
            
            if chart_data.get("success"):
                import base64
                image_data = base64.b64decode(chart_data["image"])
                await update.message.reply_photo(
                    photo=image_data,
                    caption=f"📈 <b>{symbol}</b> - Price & Volume Chart\n\n👇 <i>Enter next symbol for Chart:</i>",
                    parse_mode="HTML"
                )
                await status_msg.delete()
            else:
                await status_msg.edit_text(f"❌ Could not generate chart for {symbol}.\n👇 <i>Try another symbol:</i>", parse_mode="HTML")
        return

    if current_state == "WAITING_FOR_FUNDAMENTALS_SYMBOL":
        if text.lower() in ["back", "cancel", "exit", "main menu"]:
            USER_STATES.pop(user_id, None)
            await update.message.reply_text("❌ Cancelled.")
            await start(update, context)
            return
        
        symbol = text.upper()
        # KEEP STATE: USER_STATES.pop(user_id, None)
        status_msg = await update.message.reply_text(f"🔄 Fetching fundamentals for {symbol}...\n(Type another symbol or 'Back' to exit)")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/quote/{symbol}", headers=get_api_headers()) as resp:
                quote_data = await resp.json()
        
        # Call Backend API
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/fundamentals/{symbol}", headers=get_api_headers()) as resp:
                data = await resp.json()
        
        if data.get("success"):
            d = data.get("data", {})
            pe = d.get("pe_ratio")
            pe_str = f"{pe:.2f}" if pe else "N/A"
            roe = d.get("roe")
            roe_str = f"{roe * 100:.2f}%" if roe else "N/A"
            mc = d.get("market_cap")
            
            def fmt_mc(n):
                if not n:
                    return "N/A"
                if n >= 1e11:
                    return f"₹{n / 1e7:,.0f} Cr"
                if n >= 1e7:
                    return f"₹{n / 1e7:,.0f} Cr"
                return f"₹{n:,.0f}"
            
            mc_str = fmt_mc(mc)
            pb = d.get("pb_ratio")
            pb_str = f"{pb:.2f}" if pb else "N/A"
            div = d.get("dividend_yield")
            div_str = f"{div * 100:.2f}%" if div else "N/A"
            
            msg = (
                f"📊 <b>{symbol} Fundamentals</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"P/E Ratio: <b>{pe_str}</b>\n"
                f"ROE: <b>{roe_str}</b>\n"
                f"P/B Ratio: {pb_str}\n"
                f"Div Yield: {div_str}\n"
                f"Market Cap: {mc_str}\n"
                f"Sector: {d.get('sector', 'N/A')}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Data provided by Yahoo Finance</i>\n\n"
                f"👇 <i>Enter next symbol for Fundamentals:</i>"
            )
            await status_msg.edit_text(msg, parse_mode="HTML")
        else:
            await status_msg.edit_text(f"❌ Could not fetch fundamentals for {symbol}.\n👇 <i>Try another symbol:</i>", parse_mode="HTML")
        return

    if current_state == "WAITING_FOR_ANALYSIS_SYMBOL":
        if text.lower() in ["back", "cancel", "exit", "main menu"]:
            USER_STATES.pop(user_id, None)
            await update.message.reply_text("❌ Cancelled.")
            await start(update, context)
            return
        
        symbol = text.upper()
        # KEEP STATE: USER_STATES.pop(user_id, None)
        status_msg = await update.message.reply_text(f"🔄 Analyzing {symbol}...\n(Type another symbol or 'Back' to exit)")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/analyze/{symbol}", headers=get_api_headers()) as resp:
                analysis_data = await resp.json()
            
            async with session.get(f"{BACKEND_URL}/api/chart/{symbol}", headers=get_api_headers()) as chart_resp:
                chart_data = await chart_resp.json()
            
            if analysis_data.get("success"):
                d = analysis_data["data"]
                trend_emoji = "🚀" if d["trend"] == "BULLISH" else "📉"
                vol_emoji = "🔥" if "High" in d["vol_status"] or "Explosion" in d["vol_status"] else "📊"
                
                msg = (
                    f"🔍 <b>Analysis: {d['symbol']}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"Price: <b>₹{d['price']}</b> ({d['change_percent']:+.2f}%)\n"
                    f"Trend: <b>{d['trend']}</b> {trend_emoji}\n"
                    f"MA 20: ₹{d['ma_20']}\n"
                    f"Avg Vol (10d): {d['avg_volume']:,}\n"
                    f"Vol Today: <b>{d['volume']:,}</b>\n"
                    f"Status: {d['vol_status']} {vol_emoji}\n"
                    f"━━━━━━━━━━━━━━━━━━━"
                )
                
                if chart_data.get("success"):
                    import base64
                    image_data = base64.b64decode(chart_data["image"])
                    await update.message.reply_photo(
                        photo=image_data,
                        caption=msg + "\n\n👇 <i>Enter next symbol for Analysis:</i>",
                        parse_mode="HTML"
                    )
                    await status_msg.delete()
                else:
                    await status_msg.edit_text(msg + "\n\n👇 <i>Enter next symbol for Analysis:</i>", parse_mode="HTML")
            else:
                await status_msg.edit_text(f"❌ Could not analyze {symbol}.\n👇 <i>Try another symbol:</i>", parse_mode="HTML")
        return

    if current_state == "WAITING_FOR_PRICE_SYMBOL":
        # Allow exiting with menu keywords
        exit_keywords = ["back", "cancel", "exit", "main menu", "menu", "chart", "fundamentals", "technical analysis", "price"]
        if text.lower() in exit_keywords:
            USER_STATES.pop(user_id, None)
            await update.message.reply_text("✅ Exited Price Check.")
            await start(update, context)
            return

        symbol = text.upper()
        status_msg = await update.message.reply_text(f"💰 Checking price for {symbol}...\n(Type another symbol or 'Back' to exit)")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BACKEND_URL}/api/quote/{symbol}", headers=get_api_headers()) as resp:
                    res = await resp.json()
            
            if res and res.get("success"):
                q = res.get("data") or {}
                # Ensure q is a dict
                if not isinstance(q, dict):
                    logger.error(f"Invalid data received for {symbol}: {q}")
                    q = {}
                
                ltp = q.get("ltp", 0) or 0
                close_price = q.get("close", 0) or ltp or 1  # Fallback to LTP or 1 to avoid div/0
                diff = ltp - close_price
                pct = (diff / close_price) * 100
                emoji = "🚀" if diff >= 0 else "🔻"
                volume = q.get("volume", 0) or 0
                
                msg = (
                    f"{emoji} <b>{q.get('symbol', symbol)}</b>: ₹{ltp:,.2f}\n"
                    f"Change: {diff:+.2f} ({pct:+.2f}%)\n"
                    f"Vol: {volume:,}\n\n"
                    f"👇 <i>Enter next symbol for Price:</i>"
                )
                await status_msg.edit_text(msg, parse_mode="HTML")
            else:
                await status_msg.edit_text(f"❌ Quote not found for {symbol}.\n👇 <i>Try another symbol:</i>", parse_mode="HTML")
        except Exception as e:
            logger.error(f"Price Check Error: {e}")
            await status_msg.edit_text(f"❌ Error fetching price for {symbol}.\n👇 <i>Try another symbol:</i>")
        return

    # --- MENU HANDLERS ---
    # Intercept Greetings or "start" keyword
    if text.lower() == "start":
        await start(update, context)
        return

    if text.lower() in ["hi", "hello", "hey"]:
        await update.message.reply_text(
            "👋 <b>Welcome!</b>\nPlease type 'start' to activate the AI Financial Assistant.",
            parse_mode="HTML",
        )
        return

    if "Exit" in text or text.lower() == "exit":
        await update.message.reply_text(
            "👋 <b>Goodbye!</b>\nType 'start' anytime to wake me up.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML",
        )
        return

    if text == "📖 Readme":
        help_text = (
            "📖 <b>Pystock Bot - Your AI Stock Companion</b>\n\n"
            "<b>🔍 Smart Screener</b>\n"
            "• Use menu buttons for Breakouts/Volume shocks.\n"
            "• Type <i>'Show stocks with RSI &lt; 30'</i> for AI analysis.\n\n"
            "<b>💼 Portfolio Manager</b>\n"
            "• Add: <i>'Bought 10 TCS at 3000'</i>\n"
            "• Sell: <i>'Sold 5 TCS at 3200'</i>\n"
            "• View holdings & P&L in the menu.\n\n"
            "<b>🔔 Intelligent Alerts</b>\n"
            "• Type: <i>'Alert me if TCS > 3000'</i>\n"
            "• Real-time price notifications directly here.\n\n"
            "<b>📊 Advanced Tools</b>\n"
            "• View Interactive 📈 <b>Charts</b>.\n"
            "• Get 💎 <b>Fundamentals</b> & 📊 <b>Technical Analysis</b>.\n\n"
            "<b>📞 Support & Feedback</b>\n"
            "• Found a bug? Use <b>⚠️ Raise Issue</b>.\n"
            "• Have an idea? Use <b>📝 Provide Feedback</b>.\n"
            "• <i>(Include your email in the message for a reply!)</i>\n\n"
            "<i>Just type your request naturally!</i>"
        )
        await update.message.reply_text(help_text, parse_mode="HTML")
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
        await update.message.reply_text(policy_text, parse_mode="HTML")
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
        await update.message.reply_text(disclaimer_text, parse_mode="HTML")
        return

    if text == "🔔 Alerts":
        await update.message.reply_text(
            "🔔 <b>Alerts Mode</b>\nType: 'Alert me if TCS > 3000'", parse_mode="HTML"
        )
        return

    if text == "🔍 Screener":
        await show_screener_menu(update, context)
        return

    if text == "💼 Portfolio":
        await show_portfolio_menu(update, context)
        return

    if "my plan" in text.lower() or text == "💎 My Plan":
        # Show Sub-Menu
        keyboard = [
            [KeyboardButton("🚀 Upgrade to Pro"), KeyboardButton("🎟️ Redeem Code")],
            [KeyboardButton("🏠 Main Menu")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("💎 <b>My Plan Menu</b>", reply_markup=reply_markup, parse_mode="HTML")
        await show_plan_status(update, context)
        return
    
    if text == "📞 Contact Support":
        keyboard = [
            [KeyboardButton("⚠️ Raise Issue"), KeyboardButton("📝 Provide Feedback")],
            [KeyboardButton("🏠 Main Menu")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "📞 <b>Contact Support</b>\n\nHow can we help you today?",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return
    
    if text == "⚠️ Raise Issue":
        USER_STATES[user_id] = "WAITING_FOR_ISSUE"
        await update.message.reply_text(
            "⚠️ <b>Raise an Issue</b>\n\nPlease describe the issue you are facing.\n"
            "<i>(Tip: Include your email address if you'd like a reply!)</i>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Back")]], resize_keyboard=True)
        )
        return
        
    if text == "📝 Provide Feedback":
        USER_STATES[user_id] = "WAITING_FOR_FEEDBACK"
        await update.message.reply_text(
            "📝 <b>Provide Feedback</b>\n\nWe'd love to hear your thoughts!\n"
            "<i>(Tip: Include your email address if you'd like a reply!)</i>",
            parse_mode="HTML",
             reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Back")]], resize_keyboard=True)
        )
        return

    if text == "📊 Stock Tools":
        keyboard = [
            [KeyboardButton("📈 Chart"), KeyboardButton("💎 Fundamentals")],
            [KeyboardButton("📊 Technical Analysis")],
            [KeyboardButton("🏠 Main Menu")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "📊 <b>Stock Tools</b>\n\n"
            "Select a tool to analyze any stock:\n\n"
            "• <b>Chart:</b> View price & volume chart\n"
            "• <b>Fundamentals:</b> P/E, ROE, Market Cap, etc.\n"
            "• <b>Technical Analysis:</b> Volume trends, MA, signals",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return

    # --- NEW MENU HANDLERS ---
    if text == "🚀 Upgrade to Pro":
        msg = (
            "🚀 <b>Upgrade Your Experience!</b>\n\n"
            "Unlock the full power of Pystock with our premium plans:\n\n"
            "<b>🌟 PRO Plan</b>\n"
            "• 100 requests/day\n"
            "• Priority Support\n"
            "• Advanced Screeners\n"
            "<i>Only ₹199/month</i>\n\n"
            "<b>🔥 PREMIUM Plan</b>\n"
            "• 1000 requests/day\n"
            "• AI Deep Analysis\n"
            "• Real-time Alerts\n"
            "<i>Only ₹499/month</i>\n\n"
            "To upgrade, please contact support or use a redemption code."
        )
        # We can add inline buttons for "Contact Support" if there is a link
        await update.message.reply_text(msg, parse_mode="HTML")
        return

    if text == "🎟️ Redeem Code":
        USER_STATES[user_id] = "WAITING_FOR_CODE"
        await update.message.reply_text(
            "🎟️ <b>Redeem Access Code</b>\n\n"
            "Please enter your access code below:\n"
            "(or type 'Back' to cancel)",
            parse_mode="HTML"
        )
        return

    # --- REDEEM CODE CHECK (State Based & Command Based) ---
    # Handle Code Entry from State
    if current_state == "WAITING_FOR_CODE":
        if text.lower() in ["back", "cancel", "exit"]:
            USER_STATES.pop(user_id, None)
            await update.message.reply_text("❌ Redemption cancelled.")
            return
        
        # Treat text as code
        code = text.strip()
        # Reset state so we don't get stuck if logic fails
        USER_STATES.pop(user_id, None) 
        
        # Reuse the logic below by mocking the command structure or ensuring logic flows
        # We'll just set text to "redeem <code>" and let the next block handle it?
        # No, better to call a shared helper or just copy logic. 
        # For simplicity in this edit, I will modify the next block to handle it.
        # But wait, I can just modify the 'text' variable effectively? 
        # No, safer to just replicate the call or jump to it.
        
        # Let's just override text to trigger the command handler below
        text = f"redeem {code}"
        # proceed to next block

    if text.lower().startswith("redeem "):
        code = text.split(" ", 1)[1].strip()
        msg = await update.message.reply_text("🔄 Verifying access code...")

        async with aiohttp.ClientSession() as session:
            try:
                # Try TESTER code first
                payload = {"user_id": str(user_id), "code": code, "tier": "TESTER"}
                async with session.post(
                    f"{BACKEND_URL}/api/subscription/redeem",
                    json=payload,
                    headers=get_api_headers(),
                ) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        if res.get("success"):
                            await msg.edit_text(
                                "🎉 <b>Access Granted!</b>\nYou now have TESTER access (50 requests/day).",
                                parse_mode="HTML",
                            )
                            return
                        # If TESTER code failed, try ADMIN code
                        payload = {
                            "user_id": str(user_id),
                            "code": code,
                            "tier": "ADMIN",
                        }
                        async with session.post(
                            f"{BACKEND_URL}/api/subscription/redeem",
                            json=payload,
                            headers=get_api_headers(),
                        ) as admin_resp:
                            if admin_resp.status == 200:
                                admin_res = await admin_resp.json()
                                if admin_res.get("success"):
                                    await msg.edit_text(
                                        "🎉 <b>Access Granted!</b>\nYou now have Unlimited Admin Access.",
                                        parse_mode="HTML",
                                    )
                                    return
                            await msg.edit_text("❌ Invalid Code.")
                            return
                    elif resp.status == 500:
                        # Tester config not available, try ADMIN
                        payload = {
                            "user_id": str(user_id),
                            "code": code,
                            "tier": "ADMIN",
                        }
                        async with session.post(
                            f"{BACKEND_URL}/api/subscription/redeem",
                            json=payload,
                            headers=get_api_headers(),
                        ) as admin_resp:
                            if admin_resp.status == 200:
                                admin_res = await admin_resp.json()
                                if admin_res.get("success"):
                                    await msg.edit_text(
                                        "🎉 <b>Access Granted!</b>\nYou now have Unlimited Admin Access.",
                                        parse_mode="HTML",
                                    )
                                    return
                            await msg.edit_text("❌ Invalid Code.")
                            return
                        await msg.edit_text("❌ Codes not configured on server.")
                    else:
                        await msg.edit_text("❌ Verification failed.")
            except Exception as e:
                logger.error(f"Redeem Error: {e}")
                await msg.edit_text("❌ Connection Error.")
        return

    # --- MAIN MENU ROUTING ---
    if text == "📋 Pre-built":
        # We will show the list of scans here
        keyboard = [
            [InlineKeyboardButton("📈 Breakout Stocks", callback_data="scan_breakout")],
            [InlineKeyboardButton("🔥 Volume Shockers", callback_data="scan_volume")],
            [InlineKeyboardButton("💎 Value Stocks", callback_data="scan_value")],
            [InlineKeyboardButton("━━━ 🎯 GURU STRATEGIES ━━━", callback_data="noop")],
            [
                InlineKeyboardButton(
                    "🚀 Minervini Momentum", callback_data="guru_minervini"
                )
            ],
            [InlineKeyboardButton("📊 Peter Lynch Value", callback_data="guru_lynch")],
            [InlineKeyboardButton("💵 Warren Buffett", callback_data="guru_buffett")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📋 <b>Popular Scans</b>\nSelect one to run now:",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
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
        await update.message.reply_text(info_msg, parse_mode="HTML")
        return

    if text == "💾 Saved Scans":
        # Fetch Saved Scans
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{BACKEND_URL}/api/screener/saved?user_id={user_id}",
                    headers=get_api_headers(),
                ) as resp:
                    if resp.status == 200:
                        json_data = await resp.json()
                        scans = json_data.get("data", [])

                        if not scans:
                            await update.message.reply_text(
                                "💾 <b>Saved Scans</b>\n\nYou haven't saved any scans yet.\nTry running a custom scan and clicking 'Save'!",
                                parse_mode="HTML",
                            )
                        else:
                            keyboard = []
                            for s in scans:
                                # Row with [Run Name] [Delete]
                                # Note: Delete might be risky to put right next to it without confirmation, but for MVP ok.
                                # Or just list them to Run.
                                keyboard.append(
                                    [
                                        InlineKeyboardButton(
                                            f"🚀 {s['name']}",
                                            callback_data=f"saved_run_{s['id']}",
                                        ),
                                        InlineKeyboardButton(
                                            "❌", callback_data=f"saved_del_{s['id']}"
                                        ),
                                    ]
                                )

                            keyboard.append(
                                [
                                    InlineKeyboardButton(
                                        "🔙 Back to Screener",
                                        callback_data="back_to_screener",
                                    )
                                ]
                            )
                            reply_markup = InlineKeyboardMarkup(keyboard)

                            await update.message.reply_text(
                                "💾 <b>Your Saved Scans</b>\nSelect to Run:",
                                reply_markup=reply_markup,
                                parse_mode="HTML",
                            )
                    else:
                        await update.message.reply_text(
                            "❌ Error fetching saved scans."
                        )
            except Exception as e:
                logger.error(f"Saved Scans Error: {e}")
                await update.message.reply_text("❌ Connection Error.")
        return

    if text == "👀 View":
        # Direct portfolio fetch - no AI needed
        status_msg = await update.message.reply_text("🔄 Fetching Portfolio...")
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{BACKEND_URL}/api/portfolio/list?user_id={user_id}",
                    headers=get_api_headers(),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        holdings = data.get("holdings", [])
                        summary = data.get("summary", {})

                        if not holdings:
                            await status_msg.edit_text(
                                "💼 Your portfolio is empty.\n\nAdd stocks: 'Bought 10 TCS at 3500'"
                            )
                            return

                        total_val = summary.get("total_value", 0)
                        total_pnl = summary.get("total_pnl", 0)
                        total_pct = summary.get("total_pnl_percent", 0)

                        pnl_emoji = "💰" if total_pnl >= 0 else "📉"
                        sign = "+" if total_pnl >= 0 else ""

                        msg = "📊 <b>Your Portfolio</b>\n"
                        msg += f"Total Value: ₹{total_val:,.2f}\n"
                        msg += f"P&L: {sign}₹{total_pnl:,.2f} ({sign}{total_pct:.2f}%) {pnl_emoji}\n"
                        msg += "━━━━━━━━━━━━━━━\n"

                        for h in holdings[:10]:
                            sym = h["symbol"]
                            pnl = h["pnl"]
                            pnl_pct = h["pnl_percent"]
                            e = "🟢" if pnl >= 0 else "🔴"
                            msg += f"{e} {sym}: {'+' if pnl >= 0 else ''}₹{pnl:,.0f} ({pnl_pct:.1f}%)\n"

                        if len(holdings) > 10:
                            msg += f"\n<i>...and {len(holdings) - 10} more</i>"

                        await status_msg.edit_text(msg, parse_mode="HTML")
                    else:
                        await status_msg.edit_text("❌ Could not fetch portfolio.")
        except Exception as e:
            logger.error(f"Portfolio fetch error: {type(e).__name__}: {e}")
            await status_msg.edit_text(f"❌ Connection error: {type(e).__name__}")
        return

    if text == "❓ Help":
        await update.message.reply_text("❓ Help: Try: 'Alert if RELIANCE > 2500' or 'Bought 50 INFY at 1400'")
        return

    # --- STOCK TOOLS HANDLERS ---
    if text == "📈 Chart":
        USER_STATES[user_id] = "WAITING_FOR_CHART_SYMBOL"
        await update.message.reply_text(
            "📈 <b>Stock Chart</b>\n\n"
            "Enter the stock symbol (e.g., HDFC, TCS, RELIANCE):",
            parse_mode="HTML"
        )
        return

    if text == "💎 Fundamentals":
        USER_STATES[user_id] = "WAITING_FOR_FUNDAMENTALS_SYMBOL"
        await update.message.reply_text(
            "💎 <b>Stock Fundamentals</b>\n\n"
            "Enter the stock symbol (e.g., HDFC, TCS, RELIANCE):",
            parse_mode="HTML"
        )
        return

    if text == "📊 Technical Analysis":
        USER_STATES[user_id] = "WAITING_FOR_ANALYSIS_SYMBOL"
        await update.message.reply_text(
            "📊 <b>Technical Analysis</b>\n\n"
            "Enter the stock symbol (e.g., HDFC, TCS, RELIANCE):",
            parse_mode="HTML"
        )
        return

    if text in ["🔙 Back", "🏠 Main Menu", "Back", "Main Menu"]:
        await start(update, context)
        return

    # --- NEW: DIRECT STOCK SHORTCUT ---
    # If text is short and looks like a symbol, offer tools immediately
    clean_text = text.strip()
    is_symbol_candidate = (
        len(clean_text) < 30
        and len(clean_text.split()) <= 3
        and not any(c in text for c in ["/", ">", "<", "="])
        and clean_text.lower() not in ["hi", "hello", "help", "start", "exit", "menu", "back"]
        and not clean_text.endswith("?")
    )

    if is_symbol_candidate:
        potential_symbol = clean_text.upper()
        # Offer Quick Tools
        keyboard = [
            [
                InlineKeyboardButton("📈 Chart", callback_data=f"tool_chart_{potential_symbol}"),
                InlineKeyboardButton("💎 Fundamentals", callback_data=f"tool_fund_{potential_symbol}")
            ],
            [
                InlineKeyboardButton("📊 Technical Analysis", callback_data=f"tool_ta_{potential_symbol}"),
                InlineKeyboardButton("💰 Just Price", callback_data=f"tool_price_{potential_symbol}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg_text = (
            f"🔎 <b>Is '{potential_symbol}' a stock?</b>\n\n"
            f"Select a tool to analyze it directly:"
        )
        await update.message.reply_text(msg_text, reply_markup=reply_markup, parse_mode="HTML")
        return

    # --- AI PROCESSING ---
    status_msg = await update.message.reply_text("🤔 Analysing...")

    # Retrieve Context (last symbol)
    user_context_data = USER_CONTEXT.get(user_id, {})

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/api/alert/create",
                json={
                    "user_id": str(user_id),
                    "query": text,
                    "context": user_context_data,  # Pass context
                },
                headers=get_api_headers(),
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    await status_msg.edit_text(
                        f"❌ Backend Error {response.status}: {text[:50]}"
                    )
                    return

                result = await response.json()

        # --- HANDLE SCENARIOS ---
        status = result.get("status")
        intent = result.get("intent")

        if status == "NEEDS_CLARIFICATION":
            q_text = result.get('question') or "Could not understand request."
            await status_msg.edit_text(f"❓ {q_text}")

        elif status == "REJECTED":
            await status_msg.edit_text(f"🛑 {result.get('message')}")

        elif status == "MARKET_INFO":
            await status_msg.edit_text(f"💡 {result.get('message')}")

        elif status == "CREATED":
            await status_msg.edit_text(result.get("message"))
            # Save context if symbol present
            if result.get("config", {}).get("symbol"):
                USER_CONTEXT[user_id] = {
                    "last_symbol": result.get("config", {}).get("symbol")
                }

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
                async with session.get(
                    f"{BACKEND_URL}/api/portfolio/list?user_id={user_id}",
                    headers=get_api_headers(),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        holdings = data.get("holdings", [])
                        summary = data.get("summary", {})

                        if not holdings:
                            await status_msg.edit_text("💼 Your portfolio is empty.")
                        else:
                            # 1. HEADER
                            total_val = summary.get("total_value", 0)
                            total_pnl = summary.get("total_pnl", 0)
                            total_pct = summary.get("total_pnl_percent", 0)
                            ai_insight = data.get("ai_insight")

                            pnl_emoji = "💰" if total_pnl >= 0 else "📉"
                            sign = "+" if total_pnl >= 0 else ""

                            msg = "📊 <b>Your Portfolio</b>\n"
                            msg += f"Total Value: ₹{total_val:,.2f}\n"
                            msg += f"Total P&L: {sign}₹{total_pnl:,.2f} ({sign}{total_pct:,.2f}%) {pnl_emoji}\n"

                            if ai_insight:
                                msg += (
                                    f"\n💡 <b>AI Analysis:</b>\n<i>{ai_insight}</i>\n"
                                )

                            msg += "━━━━━━━━━━━━━━━━━━━\n\n"

                            # 2. HOLDINGS LIST
                            for h in holdings:
                                sym = h["symbol"]
                                qty = h["quantity"]
                                avg = h["avg_price"]
                                ltp = h["ltp"]
                                pnl = h["pnl"]
                                pnl_pct = h["pnl_percent"]
                                val = h["current_value"]

                                row_emoji = "📈" if pnl >= 0 else "📉"
                                row_sign = "+" if pnl >= 0 else ""

                                msg += f"<b>{sym}</b> | {qty} shares\n"
                                msg += f"Buy: ₹{avg:,.2f} → Now: ₹{ltp:,.2f}\n"
                                # msg += f"P&L: {row_sign}₹{pnl:,.2f} ({row_sign}{pnl_pct:,.2f}%) {row_emoji}\n" # Simplified list
                                msg += f"Value: ₹{val:,.2f} ({row_sign}{pnl_pct:,.2f}%) {row_emoji}\n\n"

                            msg += "━━━━━━━━━━━━━━━━━━━\n"
                            msg += "Last updated: Just now"

                            # 3. INLINE BUTTONS
                            keyboard = [
                                [
                                    InlineKeyboardButton(
                                        "Details", callback_data="p_details"
                                    ),
                                    InlineKeyboardButton(
                                        "Performance", callback_data="p_perf"
                                    ),
                                    InlineKeyboardButton(
                                        "Add Position", callback_data="p_add"
                                    ),
                                ]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)

                            await status_msg.edit_text(
                                msg, parse_mode="HTML", reply_markup=reply_markup
                            )
                    else:
                        await status_msg.edit_text("❌ Failed to fetch portfolio.")

        elif status == "FUNDAMENTALS":
            d = result.get("data", {})
            symbol = d.get("symbol", "Stock")

            # Format numbers
            pe = d.get("pe_ratio")
            pe_str = f"{pe:.2f}" if pe else "N/A"

            roe = d.get("roe")
            roe_str = f"{roe * 100:.2f}%" if roe else "N/A"

            mc = d.get("market_cap")

            def fmt_mc(n):
                if not n:
                    return "N/A"
                if n >= 1e11:
                    return f"₹{n / 1e7:,.0f} Cr"  # > 1B
                if n >= 1e7:
                    return f"₹{n / 1e7:,.0f} Cr"
                return f"₹{n:,.0f}"

            mc_str = fmt_mc(mc)
            pb = d.get("pb_ratio")
            pb_str = f"{pb:.2f}" if pb else "N/A"
            div = d.get("dividend_yield")
            div_str = f"{div * 100:.2f}%" if div else "N/A"

            msg = (
                f"📊 <b>{symbol} Fundamentals</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"P/E Ratio: <b>{pe_str}</b>\n"
                f"ROE: <b>{roe_str}</b>\n"
                f"P/B Ratio: {pb_str}\n"
                f"Div Yield: {div_str}\n"
                f"Market Cap: {mc_str}\n"
                f"Sector: {d.get('sector', 'N/A')}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Data provided by Yahoo Finance</i>"
            )
            await status_msg.edit_text(msg, parse_mode="HTML")

        elif intent == "CHECK_PRICE":
            symbol = result.get("data", {}).get("symbol")
            if not symbol:
                await status_msg.edit_text("❓ Which stock?")
            else:
                # Store Context
                USER_CONTEXT[user_id] = {"last_symbol": symbol}

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{BACKEND_URL}/api/quote/{symbol}", headers=get_api_headers()
                    ) as resp:
                        if resp.status == 200:
                            json_res = await resp.json()
                            if json_res.get("success"):
                                q = json_res["data"]

                                emoji = "🚀" if q["ltp"] >= q["close"] else "🔻"
                                color = "🟢" if q["ltp"] >= q["close"] else "🔴"
                                diff = q["ltp"] - q["close"]
                                pct = (diff / q["close"]) * 100 if q["close"] > 0 else 0

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
                                await status_msg.edit_text(msg, parse_mode="HTML")
                            else:
                                await status_msg.edit_text(
                                    f"❌ Could not find quote for {symbol}."
                                )
                        else:
                            await status_msg.edit_text("❌ Quote Service Error.")

        elif intent == "ANALYZE_STOCK":
            symbol = result.get("data", {}).get("symbol")
            if not symbol:
                 await status_msg.edit_text("❓ Which stock?")
            else:
                 # Fetch Analysis
                 async with aiohttp.ClientSession() as session:
                     # 1. Get Text Analysis
                     async with session.get(f"{BACKEND_URL}/api/analyze/{symbol}", headers=get_api_headers()) as resp:
                         analysis_data = await resp.json()
                     
                     # 2. Get Chart (Image)
                     async with session.get(f"{BACKEND_URL}/api/chart/{symbol}", headers=get_api_headers()) as chart_resp:
                         chart_data = await chart_resp.json()
                     
                     if analysis_data.get("success"):
                         d = analysis_data["data"]
                         
                         trend_emoji = "🚀" if d["trend"] == "BULLISH" else "📉"
                         vol_emoji = "🔥" if "High" in d["vol_status"] or "Explosion" in d["vol_status"] else "📊"
                         
                         msg = (
                             f"🔍 <b>Analysis: {d['symbol']}</b>\n"
                             f"━━━━━━━━━━━━━━━━━━━\n"
                             f"Price: <b>₹{d['price']}</b> ({d['change_percent']:+.2f}%)\n"
                             f"Trend: <b>{d['trend']}</b> {trend_emoji}\n"
                             f"Avg Vol (10d): {d['avg_volume']:,}\n"
                             f"Vol Today: <b>{d['volume']:,}</b>\n"
                             f"Status: {d['vol_status']} {vol_emoji}\n"
                             f"━━━━━━━━━━━━━━━━━━━"
                         )
                         
                         # Send Chart if available
                         if chart_data.get("success"):
                             import base64
                             image_data = base64.b64decode(chart_data["image"])
                             await update.message.reply_photo(
                                 photo=image_data,
                                 caption=msg,
                                 parse_mode="HTML"
                             )
                             await status_msg.delete() # Remove "Analysing..." message
                         else:
                             await status_msg.edit_text(msg, parse_mode="HTML")
                     else:
                         await status_msg.edit_text(f"❌ Could not analyze {symbol}.")
                         
        elif status == "ANALYZE_STOCK":
            # Handle when backend returns status directly
            symbol = result.get("symbol") or result.get("data", {}).get("symbol")
            if not symbol:
                await status_msg.edit_text("❓ Which stock?")
            else:
                # Fetch Analysis
                async with aiohttp.ClientSession() as session:
                    # 1. Get Text Analysis
                    async with session.get(f"{BACKEND_URL}/api/analyze/{symbol}", headers=get_api_headers()) as resp:
                        analysis_data = await resp.json()
                    
                    # 2. Get Chart (Image)
                    async with session.get(f"{BACKEND_URL}/api/chart/{symbol}", headers=get_api_headers()) as chart_resp:
                        chart_data = await chart_resp.json()
                    
                    if analysis_data.get("success"):
                        d = analysis_data["data"]
                        
                        trend_emoji = "🚀" if d["trend"] == "BULLISH" else "📉"
                        vol_emoji = "🔥" if "High" in d["vol_status"] or "Explosion" in d["vol_status"] else "📊"
                        
                        msg = (
                            f"🔍 <b>Analysis: {d['symbol']}</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"Price: <b>₹{d['price']}</b> ({d['change_percent']:+.2f}%)\n"
                            f"Trend: <b>{d['trend']}</b> {trend_emoji}\n"
                            f"Avg Vol (10d): {d['avg_volume']:,}\n"
                            f"Vol Today: <b>{d['volume']:,}</b>\n"
                            f"Status: {d['vol_status']} {vol_emoji}\n"
                            f"━━━━━━━━━━━━━━━━━━━"
                        )
                        
                        # Send Chart if available
                        if chart_data.get("success"):
                            import base64
                            image_data = base64.b64decode(chart_data["image"])
                            await update.message.reply_photo(
                                photo=image_data,
                                caption=msg,
                                parse_mode="HTML"
                            )
                            await status_msg.delete() # Remove "Analysing..." message
                        else:
                            await status_msg.edit_text(msg, parse_mode="HTML")
                    else:
                        await status_msg.edit_text(f"❌ Could not analyze {symbol}.")
                          
        elif status == "ERROR":
            await status_msg.edit_text(
                f"❌ {result.get('message', 'An error occurred.')}"
            )

        else:
            await status_msg.edit_text("⚠️ Unknown Response.")

    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text("❌ System Error.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()  # Acknowledge interaction

    data = query.data
    user_id = update.effective_user.id

    if data == "p_add":
        await query.message.reply_text(
            "📝 <b>Add Holding</b>\nType: 'Bought 10 TCS at 3000'", parse_mode="HTML"
        )

    elif data == "save_scan":
        # Check if we have context
        last_query = USER_CONTEXT.get(user_id, {}).get("last_query")
        if not last_query:
            await query.answer("No scan to save!", show_alert=True)
            return

        USER_STATES[user_id] = "WAITING_FOR_SCAN_NAME"
        await query.message.reply_text(
            "💾 <b>Name your Scan:</b>\nType a name (e.g., 'Oversold RSI')",
            parse_mode="HTML",
        )

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
            async with session.get(
                f"{BACKEND_URL}/api/screener/saved?user_id={user_id}",
                headers=get_api_headers(),
            ) as resp:
                if resp.status == 200:
                    json_data = await resp.json()
                    scans = json_data.get("data", [])
                    target = next((s for s in scans if str(s["id"]) == scan_id), None)

                    if target:
                        query_text = target["query"]
                        await query.message.reply_text(
                            f"🚀 Running saved scan: <b>{target['name']}</b>",
                            parse_mode="HTML",
                        )
                        # Trigger existing Custom AI logic by simulated text?
                        # No, just reuse code or call API directly. Direct API call is cleaner.

                        payload = {"user_id": str(user_id), "query": query_text}
                        async with session.post(
                            f"{BACKEND_URL}/api/screener/custom",
                            json=payload,
                            headers=get_api_headers(),
                        ) as scan_resp:
                            # ... Same result rendering logic as Custom AI ...
                            if scan_resp.status == 200:
                                r_json = await scan_resp.json()
                                results = r_json.get("data", [])
                                count = r_json.get("count", 0)

                                msg = f"🔍 <b>Results for '{target['name']}':</b>\n\n"
                                msg += f"{'Symbol':<10} {'Price'}\n━━━━━━━━━━━━━\n"
                                for r in results[:10]:
                                    msg += f"{r['symbol']:<10} ₹{r['ltp']}\n"
                                if count > 10:
                                    msg += f"<i>...and {count - 10} more.</i>"

                                await query.message.reply_text(
                                    f"<pre>{msg}</pre>", parse_mode="HTML"
                                )
                            else:
                                await query.message.reply_text("❌ Scan failed.")
                    else:
                        await query.message.reply_text("❌ Scan not found.")

    elif data.startswith("saved_del_"):
        scan_id = data.split("_")[2]
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{BACKEND_URL}/api/screener/saved/{scan_id}?user_id={user_id}",
                headers=get_api_headers(),
            ) as resp:
                if resp.status == 200:
                    await query.answer("Scan Deleted!", show_alert=True)
                    # Refresh list? Ideally yes, but for now just acknowledge.
                    await query.message.delete()  # Remove button list
                    await query.message.reply_text("🗑️ Scan Deleted.")
                else:
                    await query.answer("Delete Failed", show_alert=True)


    elif data.startswith("tool_"):
        # tool_chart_SYMBOL, tool_fund_SYMBOL, tool_ta_SYMBOL, tool_price_SYMBOL
        parts = data.split("_", 2)
        action = parts[1]
        symbol = parts[2]
        
        user_id = update.effective_user.id
        
        if action == "chart":
            await query.message.reply_text(f"📊 Generating chart for {symbol}...")
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BACKEND_URL}/api/chart/{symbol}", headers=get_api_headers()) as resp:
                    chart_data = await resp.json()
                
                if chart_data.get("success"):
                    import base64
                    image_data = base64.b64decode(chart_data["image"])
                    await query.message.reply_photo(
                        photo=image_data,
                        caption=f"📈 <b>{symbol}</b> - Price & Volume Chart",
                        parse_mode="HTML"
                    )
                else:
                    await query.message.reply_text(f"❌ Could not generate chart for {symbol}.")
                    
        elif action == "fund":
            await query.message.reply_text(f"🔄 Fetching fundamentals for {symbol}...")
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BACKEND_URL}/api/fundamentals/{symbol}", headers=get_api_headers()) as resp:
                    data = await resp.json()
            
            if data.get("success"):
                d = data.get("data", {})
                pe = d.get("pe_ratio")
                pe_str = f"{pe:.2f}" if pe else "N/A"
                roe = d.get("roe")
                roe_str = f"{roe * 100:.2f}%" if roe else "N/A"
                mc = d.get("market_cap")
                def fmt_mc(n):
                    if not n: return "N/A"
                    if n >= 1e7: return f"₹{n / 1e7:,.0f} Cr"
                    return f"₹{n:,.0f}"
                
                msg = (
                    f"📊 <b>{symbol} Fundamentals</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"P/E Ratio: <b>{pe_str}</b>\n"
                    f"ROE: <b>{roe_str}</b>\n"
                    f"P/B Ratio: {d.get('pb_ratio', 'N/A')}\n"
                    f"Market Cap: {fmt_mc(mc)}\n"
                    f"Sector: {d.get('sector', 'N/A')}\n"
                    f"━━━━━━━━━━━━━━━━━━━"
                )
                await query.message.reply_text(msg, parse_mode="HTML")
            else:
                await query.message.reply_text(f"❌ Could not fetch fundamentals for {symbol}.")

        elif action == "ta":
            await query.message.reply_text(f"🔄 Analyzing {symbol}...")
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BACKEND_URL}/api/analyze/{symbol}", headers=get_api_headers()) as resp:
                    analysis = await resp.json()
                
                if analysis.get("success"):
                    d = analysis["data"]
                    trend = "🚀" if d["trend"] == "BULLISH" else "📉"
                    msg = (
                        f"🔍 <b>Analysis: {d['symbol']}</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"Price: <b>₹{d['price']}</b> ({d['change_percent']:+.2f}%)\n"
                        f"Trend: <b>{d['trend']}</b> {trend}\n"
                        f"Vol Status: {d['vol_status']}\n"
                        f"━━━━━━━━━━━━━━━━━━━"
                    )
                    await query.message.reply_text(msg, parse_mode="HTML")
                else:
                    await query.message.reply_text(f"❌ Could not analyze {symbol}.")
        
        elif action == "price":
             # Trigger price check logic AND set state
             USER_STATES[user_id] = "WAITING_FOR_PRICE_SYMBOL"
             await query.message.reply_text(f"💰 Checking price for {symbol}...\n(Type another symbol or 'Back' to exit)")
             
             try:
                 async with aiohttp.ClientSession() as session:
                    async with session.get(f"{BACKEND_URL}/api/quote/{symbol}", headers=get_api_headers()) as resp:
                        res = await resp.json()
                        
                 if res and res.get("success"):
                    q = res.get("data") or {}
                    if not isinstance(q, dict):
                        q = {}
                        
                    ltp = q.get("ltp", 0) or 0
                    close_price = q.get("close", 0) or ltp or 1
                    diff = ltp - close_price
                    pct = (diff / close_price) * 100
                    emoji = "🚀" if diff >= 0 else "🔻"
                    volume = q.get("volume", 0) or 0
                    
                    msg = (
                        f"{emoji} <b>{q.get('symbol', symbol)}</b>: ₹{ltp:,.2f}\n"
                        f"Change: {diff:+.2f} ({pct:+.2f}%)\n"
                        f"Vol: {volume:,}\n\n"
                        f"👇 <i>Enter next symbol for Price:</i>"
                    )
                    await query.message.reply_text(msg, parse_mode="HTML")
                 else:
                    await query.message.reply_text(f"❌ Quote not found.\n👇 <i>Try another symbol:</i>", parse_mode="HTML")
             except Exception as e:
                logger.error(f"Price Button Error: {e}")
                await query.message.reply_text(f"❌ Error fetching price.")

    elif data == "p_perf":
        await query.edit_message_text("📊 Generating Performance Chart... Please wait.")

        async with aiohttp.ClientSession() as session:
            try:
                # Fetch Data
                async with session.get(
                    f"{BACKEND_URL}/api/portfolio/performance?user_id={user_id}",
                    headers=get_api_headers(),
                ) as resp:
                    if resp.status == 200:
                        json_data = await resp.json()
                        dates = json_data.get("dates", [])
                        values = json_data.get("values", [])

                        if not dates or len(dates) < 2:
                            await query.message.reply_text(
                                "📉 Not enough data for a chart yet."
                            )
                            return

                        # Generate Chart
                        import matplotlib.pyplot as plt
                        import pandas as pd
                        import io

                        # Data Prep
                        df = pd.DataFrame(
                            {"Date": pd.to_datetime(dates), "Value": values}
                        )

                        plt.figure(figsize=(10, 5))
                        plt.plot(
                            df["Date"],
                            df["Value"],
                            marker="o",
                            linestyle="-",
                            color="#007bff",
                            linewidth=2,
                            markersize=4,
                        )

                        plt.title(
                            "Portfolio Equity Curve (30 Days)",
                            fontsize=14,
                            fontweight="bold",
                        )
                        plt.xlabel("Date", fontsize=10)
                        plt.ylabel("Value (₹)", fontsize=10)
                        plt.grid(True, linestyle="--", alpha=0.6)
                        plt.xticks(rotation=45)
                        plt.tight_layout()

                        # Save to Buffer
                        buf = io.BytesIO()
                        plt.savefig(buf, format="png")
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
                        await query.message.reply_photo(
                            photo=buf, caption=caption, parse_mode="HTML"
                        )

                        # Re-show menu?
                        # await show_portfolio_menu... (Optional, but let's keep it clean)

                    else:
                        await query.message.reply_text(
                            "❌ Failed to fetch performance data."
                        )
            except Exception as e:
                logger.error(f"Chart Error: {e}")
                await query.message.reply_text("❌ Error generating chart.")

    elif data == "p_details":
        # Fetch symbols to show selection
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BACKEND_URL}/api/portfolio/list?user_id={user_id}",
                headers=get_api_headers(),
            ) as resp:
                if resp.status == 200:
                    json_data = await resp.json()
                    holdings = json_data.get("holdings", [])

                    if not holdings:
                        await query.edit_message_text("Portfolio is empty.")
                        return

                    # Create buttons for each stock
                    keyboard = []
                    for h in holdings:
                        sym = h["symbol"]
                        keyboard.append(
                            [
                                InlineKeyboardButton(
                                    f"📊 {sym}", callback_data=f"stock_{sym}"
                                )
                            ]
                        )

                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                "🔙 Back to Overview", callback_data="p_overview"
                            )
                        ]
                    )
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await query.edit_message_text(
                        "Select stock for details:", reply_markup=reply_markup
                    )
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
            async with session.get(
                f"{BACKEND_URL}/api/portfolio/list?user_id={user_id}",
                headers=get_api_headers(),
            ) as resp:
                if resp.status == 200:
                    json_data = await resp.json()
                    holdings = json_data.get("holdings", [])
                    summary = json_data.get("summary", {})

                    # 1. HEADER
                    total_val = summary.get("total_value", 0)
                    total_pnl = summary.get("total_pnl", 0)
                    total_pct = summary.get("total_pnl_percent", 0)

                    pnl_emoji = "💰" if total_pnl >= 0 else "📉"
                    sign = "+" if total_pnl >= 0 else ""

                    msg = f"📊 <b>Your Portfolio</b>\n"
                    msg += f"Total Value: ₹{total_val:,.2f}\n"
                    msg += f"Total P&L: {sign}₹{total_pnl:,.2f} ({sign}{total_pct:,.2f}%) {pnl_emoji}\n"
                    msg += "━━━━━━━━━━━━━━━━━━━\n\n"

                    # 2. HOLDINGS LIST
                    for h in holdings:
                        sym = h["symbol"]
                        qty = h["quantity"]
                        avg = h["avg_price"]
                        ltp = h["ltp"]
                        pnl = h["pnl"]
                        pnl_pct = h["pnl_percent"]
                        val = h["current_value"]

                        row_emoji = "📈" if pnl >= 0 else "📉"
                        row_sign = "+" if pnl >= 0 else ""

                        msg += f"<b>{sym}</b> | {qty} shares\n"
                        msg += f"Buy: ₹{avg:,.2f} → Now: ₹{ltp:,.2f}\n"
                        msg += f"P&L: {row_sign}₹{pnl:,.2f} ({row_sign}{pnl_pct:,.2f}%) {row_emoji}\n"
                        msg += f"Value: ₹{val:,.2f}\n\n"

                    msg += "━━━━━━━━━━━━━━━━━━━\n"
                    msg += "Last updated: Just now"

                    # Re-attach Main Buttons
                    keyboard = [
                        [
                            InlineKeyboardButton("Details", callback_data="p_details"),
                            InlineKeyboardButton("Performance", callback_data="p_perf"),
                            InlineKeyboardButton("Add Position", callback_data="p_add"),
                        ]
                    ]
                    await query.edit_message_text(
                        msg,
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )
                else:
                    await query.edit_message_text(
                        "❌ Error fetching portfolio overview."
                    )

    # --- SCREENER HANDLING ---
    elif data.startswith("scan_"):
        # scan_breakout, scan_volume...
        scan_type = data
        scan_title = data.replace("scan_", "").title()

        await query.edit_message_text(f"🔄 Running {scan_title} Scan...")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{BACKEND_URL}/api/screener/prebuilt?scan_type={scan_type}",
                    headers=get_api_headers(),
                ) as resp:
                    if resp.status == 200:
                        json_data = await resp.json()
                        results = json_data.get("data", [])
                        count = json_data.get("count", 0)

                        if not results:
                            await query.edit_message_text(
                                f"🔍 <b>{scan_title} Scan</b>\n\nNo matches found right now.",
                                parse_mode="HTML",
                            )
                            return

                        # Format Results
                        msg = f"🔍 <b>{scan_title} Results ({count})</b>\n\n"
                        msg += f"{'Symbol':<10} {'Price':<8} {'%Chg':<6}\n"
                        msg += "━━━━━━━━━━━━━━━━━━━\n"

                        # Show top 10
                        for r in results[:10]:
                            emoji = "🚀" if r["change_percent"] > 0 else "🔻"
                            msg += f"{r['symbol']:<10} {r['ltp']:<8} {r['change_percent']:<6}% {emoji}\n"

                        if count > 10:
                            msg += f"\n<i>...and {count - 10} more.</i>"

                        # Add Timestamp and Disclaimer
                        ts = results[0].get("timestamp", "Just now")
                        msg += f"\n\n🕒 Updates: {ts}"
                        msg += "\n\n📊 These stocks match technical filters.\nThis is informational only, not a recommendation."

                        # Add Action Buttons (could be Save Scan in future)
                        keyboard = [
                            [
                                InlineKeyboardButton(
                                    "🔙 Back to Menu", callback_data="back_to_screener"
                                )
                            ]
                        ]
                        await query.edit_message_text(
                            f"<pre>{msg}</pre>",
                            parse_mode="HTML",
                            reply_markup=InlineKeyboardMarkup(keyboard),
                        )
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
            [InlineKeyboardButton("💎 Value Stocks", callback_data="scan_value")],
            [InlineKeyboardButton("━━━ 🎯 GURU STRATEGIES ━━━", callback_data="noop")],
            [
                InlineKeyboardButton(
                    "🚀 Minervini Momentum", callback_data="guru_minervini"
                )
            ],
            [InlineKeyboardButton("📊 Peter Lynch Value", callback_data="guru_lynch")],
            [InlineKeyboardButton("💵 Warren Buffett", callback_data="guru_buffett")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📋 <b>Popular Scans</b>\nSelect one to run now:",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

    elif data.startswith("guru_"):
        # guru_minervini, guru_lynch, guru_buffett
        guru_type = data.replace("guru_", "")
        guru_titles = {
            "minervini": "🚀 Mark Minervini (SEPA)",
            "lynch": "📊 Peter Lynch (PEG)",
            "buffett": "💵 Warren Buffett (Value)",
        }
        guru_title = guru_titles.get(guru_type, guru_type.title())

        await query.edit_message_text(f"🔄 Running {guru_title} Scan...")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{BACKEND_URL}/api/screener/guru?guru={guru_type}",
                    headers=get_api_headers(),
                ) as resp:
                    if resp.status == 200:
                        json_data = await resp.json()
                        results = json_data.get("data", [])
                        count = json_data.get("count", 0)
                        guru_name = json_data.get("guru", guru_title)
                        description = json_data.get("description", "")

                        if not results:
                            await query.edit_message_text(
                                f"🎯 <b>{guru_name}</b>\n<i>{description}</i>\n\n"
                                "No stocks match this strategy right now.\n"
                                "Fundamentals are cached daily - check back later!",
                                parse_mode="HTML",
                            )
                            return

                        # Format Results
                        msg = f"🎯 <b>{guru_name}</b>\n<i>{description}</i>\n\n"
                        msg += f"<b>Matches ({count}):</b>\n"
                        msg += f"{'Symbol':<10} {'P/E':<6} {'ROE':<6} {'Price'}\n"
                        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"

                        # Show top 10
                        for r in results[:10]:
                            pe = r.get("pe", 0)
                            roe = r.get("roe", 0)
                            msg += f"{r['symbol']:<10} {pe:<6} {roe:.1f}% ₹{r['ltp']:,.0f}\n"

                        if count > 10:
                            msg += f"\n<i>...and {count - 10} more.</i>"

                        msg += "\n\n📊 These stocks match guru criteria.\nThis is informational only, not a recommendation."

                        keyboard = [
                            [
                                InlineKeyboardButton(
                                    "🔙 Back to Menu", callback_data="back_to_screener"
                                )
                            ]
                        ]
                        await query.edit_message_text(
                            f"<pre>{msg}</pre>",
                            parse_mode="HTML",
                            reply_markup=InlineKeyboardMarkup(keyboard),
                        )
                    else:
                        await query.edit_message_text("❌ Guru Screener Unavailable.")
            except Exception as e:
                logger.error(f"Bot Guru Scanner Error: {e}")
                await query.edit_message_text("❌ Error connecting to Guru Screener.")

    elif data == "noop":
        # Do nothing for separator button
        await query.answer()

    elif data.startswith("stock_"):
        symbol = data.split("_")[1]

        # Fetch specific details
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BACKEND_URL}/api/portfolio/list?user_id={user_id}",
                headers=get_api_headers(),
            ) as resp:
                if resp.status == 200:
                    json_data = await resp.json()
                    holdings = json_data.get("holdings", [])

                    # Find specific holding
                    target = next((h for h in holdings if h["symbol"] == symbol), None)

                    if target:
                        # RENDER DETAILED CARD
                        # Fields: symbol, quantity, avg_price, ltp, current_value, pnl, pnl_percent, invested, day_change, day_change_percent, day_pnl, high, low

                        pnl_sign = "+" if target["pnl"] >= 0 else ""
                        day_sign = "+" if target["day_change"] >= 0 else ""

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

                        keyboard = [
                            [
                                InlineKeyboardButton(
                                    "🔙 Back to List", callback_data="p_details"
                                )
                            ]
                        ]
                        await query.edit_message_text(
                            msg,
                            parse_mode="HTML",
                            reply_markup=InlineKeyboardMarkup(keyboard),
                        )
                    else:
                        await query.edit_message_text("❌ Stock not found.")

    elif data.startswith("sub_upgrade_"):
        # Payment Integration Pending
        await query.answer("🚧 Payments Coming Soon!", show_alert=True)
        await query.message.edit_text(
            "🚧 <b>Coming Soon!</b>\n\n"
            "We are currently integrating a secure payment gateway (Razorpay).\n"
            "Stay tuned for updates!",
            parse_mode="HTML",
        )

    elif data == "back_to_menu":
        # Delete the old message to clean up
        try:
            await query.message.delete()
        except:
            pass

        # Send the main menu again (re-using start logic)
        await start(update, context)


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

    # Define commands list - REMOVED to hide the "3 blue lines" menu
    async def post_init(application: Application):
        await application.bot.delete_my_commands()
        logger.info("🗑️ Existing bot commands deleted (Hiding menu button)")

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
        print(f"[DEBUG] WEBHOOK_URL detected: {WEBHOOK_URL}")
        # Attach post_init
        application.post_init = post_init

        application.add_handler(CommandHandler("start", start))
        print("[DEBUG] Registered /start handler")
        application.add_handler(CommandHandler("plan", cmd_plan_alias))
        print("[DEBUG] Registered /plan handler -> show_plan_status")
        application.add_handler(CommandHandler("screener", cmd_screen_alias))
        print("[DEBUG] Registered /screener handler -> show_screener_menu")
        application.add_handler(CommandHandler("portfolio", cmd_port_alias))
        print("[DEBUG] Registered /portfolio handler -> show_portfolio_menu")
        application.add_handler(CommandHandler("help", cmd_help_alias))

        # New Handlers
        application.add_handler(CommandHandler("scan", scan_command))
        application.add_handler(CommandHandler("alert", alert_command))
        application.add_handler(CommandHandler("analyze", analyze_command))
        print("[DEBUG] Registered /help handler")

        # New Handlers
        application.add_handler(CommandHandler("scan", scan_command))
        application.add_handler(CommandHandler("alert", alert_command))
        application.add_handler(CommandHandler("analyze", analyze_command))

        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        application.add_handler(CallbackQueryHandler(button_handler))

        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
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

        # New Handlers
        application.add_handler(CommandHandler("scan", scan_command))
        application.add_handler(CommandHandler("alert", alert_command))
        application.add_handler(CommandHandler("analyze", analyze_command))

        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        application.add_handler(CallbackQueryHandler(button_handler))

        application.run_polling()


if __name__ == "__main__":
    main()
