from fastapi import FastAPI, HTTPException, Depends
import logging
from pydantic import BaseModel
import os
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

# Core Modules
from app.core.ai import AIAlertInterpreter 
from app.db.base import Base, engine, get_db
from app.db.models import Alert, TradeHistory
from app.core.market_data import MarketDataService
from app.core.scanner import MarketScannerService
from app.core.scheduler import AlertMonitor
from app.core.rate_limiter import custom_limiter
from app.core.subscription import get_user_tier

# Initialize Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Intelligent Alert System")

# Security Middleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# CORS - Configured for production
# Since this is a Telegram bot backend (not web frontend), we allow:
# 1. Railway's internal network (for bot <-> backend communication)
# 2. Localhost for local development
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Environment-configurable
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Specific methods only
    allow_headers=["*"],
    max_age=600,
)

market_data = MarketDataService()
scanner_service = MarketScannerService(market_data)
monitor_service = AlertMonitor()

# Startup event is defined later after all route definitions (line ~338)


@app.get("/api/quote/{symbol}")
async def get_quote(symbol: str):
    """Fetches live quote for a symbol."""
    # Input Validation
    from app.core.security import validate_symbol
    if not validate_symbol(symbol.upper()):
        raise HTTPException(status_code=400, detail="Invalid symbol format")
    
    quote = market_data.get_quote(symbol.upper())
    if quote:
        return {"success": True, "data": quote}
    return {"success": False, "message": "Symbol not found or Market Data error."}


class UserRegisterRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

@app.post("/api/auth/register")
def register_user(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register or Update a Telegram User."""
    from app.db.models import User
    
    try:
        # Check if user exists
        user = db.query(User).filter(User.telegram_id == int(payload.telegram_id)).first()
        
        if not user:
            # Create new
            user = User(
                telegram_id=int(payload.telegram_id),
                username=payload.username,
                first_name=payload.first_name,
                last_name=payload.last_name
            )
            
            # Check for Admin Override
            admin_ids = os.getenv("ADMIN_IDS", "").split(",")
            if str(payload.telegram_id) in admin_ids:
                user.subscription_tier = "ADMIN"
                
            db.add(user)
            db.commit()
            return {"success": True, "message": "User Registered", "user_id": user.telegram_id, "is_new": True}
        else:
            # Update existing
            if payload.username: user.username = payload.username
            if payload.first_name: user.first_name = payload.first_name
            if payload.last_name: user.last_name = payload.last_name
            
            # Re-check Admin (in case added to env later)
            admin_ids = os.getenv("ADMIN_IDS", "").split(",")
            if str(payload.telegram_id) in admin_ids and user.subscription_tier != "ADMIN":
                user.subscription_tier = "ADMIN"
            
            db.commit()
            return {"success": True, "message": "User Updated", "user_id": user.telegram_id, "is_new": False}
            
    except Exception as e:
        return {"success": False, "message": str(e)}

class AlertQuery(BaseModel):
    user_id: str
    query: str

@app.post("/api/screener/custom")
async def custom_screen(query_payload: AlertQuery, db: Session = Depends(get_db)): # Re-using AlertQuery {user_id, query}
    """
    1. Parse NL Query -> JSON Filters
    2. Fetch Redis Snapshot
    3. Filter Data
    """
    # Input Validation
    from app.core.security import sanitize_query
    sanitized_query = sanitize_query(query_payload.query)
    if not sanitized_query:
        raise HTTPException(status_code=400, detail="Invalid query: too short or contains unsafe characters")
    
    # Rate Limit Check
    tier = get_user_tier(query_payload.user_id, db)
    if not custom_limiter.is_allowed(query_payload.user_id, tier):
        raise HTTPException(status_code=429, detail="Daily rate limit exceeded. Upgrade to Pro/Premium for more.")

    user_query = query_payload.query
    
    # 1. AI Parse
    ai = AIAlertInterpreter()
    parsed = await ai.parse_screener_query(user_query)
    
    if "error" in parsed:
        return {"success": False, "message": "Could not understand query."}
        
    filters = parsed.get("filters", [])
    if not filters:
        return {"success": False, "message": "No valid criteria found."}
        
    # 2. Fetch Data
    symbols = scanner_service.symbols
    pipe = scanner_service.r.pipeline()
    for sym in symbols:
        pipe.hgetall(f"stock:{sym}")
    data_list = pipe.execute()
    
    results = []
    
    # 3. Apply Filters
    for item in data_list:
        if not item: continue
        
        try:
            # Convert Redis Map to Float
            ltp = float(item.get("ltp", 0))
            change = float(item.get("change_percent", 0))
            volume = float(item.get("volume", 0))
            rsi = float(item.get("rsi", 50))
            
            match = True
            for f in filters:
                field = f["field"]
                op = f["op"]
                val = f["value"]
                
                # Check mapping (ltp, volume, etc)
                data_val = 0
                if field == "ltp": data_val = ltp
                elif field == "change_pct": data_val = change
                elif field == "volume": data_val = volume
                elif field == "rsi": data_val = rsi
                
                if op == "gt" and not (data_val > val): match = False
                elif op == "lt" and not (data_val < val): match = False
                elif op == "eq" and not (data_val == val): match = False
            
            if match:
                 results.append({
                    "symbol": item.get("symbol"),
                    "ltp": ltp,
                    "change_percent": change,
                    "timestamp": item.get("timestamp", "Just now"),
                    "match_reason": "AI Match"
                })
        except Exception as e:
            continue
            
    return {"success": True, "count": len(results), "data": results, "filters_used": filters}

@app.get("/api/screener/prebuilt")
async def prebuilt_screen(scan_type: str):
    """
    Execute popular pre-defined scans.
    """
    
    # Define Criteria
    # 1. Breakout: > 4% Change
    # 2. Volume: NOT IMPLEMENTED FULLY (needs avg vol), using high raw volume for now.
    # 3. Value: RSI < 35
    
    symbols = scanner_service.symbols
    pipe = scanner_service.r.pipeline()
    for sym in symbols:
        pipe.hgetall(f"stock:{sym}")
    data_list = pipe.execute()
    
    results = []
    for item in data_list:
        if not item: continue
        try:
            ltp = float(item.get("ltp", 0))
            change = float(item.get("change_percent", 0))
            volume = float(item.get("volume", 0))
            rsi = float(item.get("rsi", 50))
            
            match = False
            
            if scan_type == "scan_breakout":
                if change > 4.0: match = True
                
            elif scan_type == "scan_volume":
                avg_vol = float(item.get("avg_volume", 1_000_000))
                # Logic: Volume > 2.5x Average Volume
                if volume > (avg_vol * 2.5): match = True
                
            elif scan_type == "scan_value":
                if rsi < 35.0: match = True
                
            if match:
                # Clean Data types for JSON response
                # Clean Data types for JSON response
                cleaned_item = {
                    "symbol": item.get("symbol"),
                    "ltp": ltp,
                    "change_percent": change,
                    "volume": int(volume),
                    "rsi": rsi,
                    "timestamp": item.get("timestamp", "Just now")
                }
                results.append(cleaned_item)
                
        except:
            continue
            
    # Sort results
    if scan_type == "scan_breakout":
        results.sort(key=lambda x: float(x.get("change_percent", 0)), reverse=True)
    elif scan_type == "scan_value":
        results.sort(key=lambda x: float(x.get("rsi", 50)))
        
    return {"success": True, "count": len(results), "data": results}
    


class SaveScanRequest(BaseModel):
    user_id: str
    name: str
    query: str

@app.post("/api/screener/save")
def save_scan(payload: SaveScanRequest, db: Session = Depends(get_db)):
    """Save a custom query."""
    try:
        from app.db.models import SavedScan
        new_scan = SavedScan(
            user_id=int(payload.user_id),
            name=payload.name,
            query=payload.query
        )
        db.add(new_scan)
        db.commit()
        return {"success": True, "message": f"Saved '{payload.name}'!"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/api/screener/saved")
def list_saved_scans(user_id: str, db: Session = Depends(get_db)):
    """List saved scans for a user."""
    try:
        from app.db.models import SavedScan
        scans = db.query(SavedScan).filter(SavedScan.user_id == int(user_id)).all()
        return {
            "success": True, 
            "data": [{"id": s.id, "name": s.name, "query": s.query} for s in scans]
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.delete("/api/screener/saved/{scan_id}")
def delete_saved_scan(scan_id: int, user_id: str, db: Session = Depends(get_db)):
    """Delete a saved scan."""
    try:
        from app.db.models import SavedScan
        db.query(SavedScan).filter(
            SavedScan.id == scan_id,
            SavedScan.user_id == int(user_id)
        ).delete()
        db.commit()
        return {"success": True, "message": "Scan deleted."}
    except Exception as e:
        return {"success": False, "message": str(e)}

class AlertResponse(BaseModel):
    success: bool
    status: str
    config: Optional[Dict[str, Any]] = None
    question: Optional[str] = None
    missing_info: Optional[List[str]] = None
    message: Optional[str] = None
    intent: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

@app.on_event("startup")
async def startup_event():
    """Complete startup sequence for all services."""
    logger = logging.getLogger("uvicorn")

    # Initialize yfinance data service
    logger.info("Initializing yfinance data service...")
    if market_data.login():
        logger.info("✅ Market Data Service Ready")
    else:
        logger.warning("⚠️ Failed to initialize Market Data Service")

    # Start Scanner Loop (requires market data)
    scanner_service.start()

    # Start Alert Monitor
    await monitor_service.start()

    logger.info("🚀 All services started successfully")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "backend"}

@app.get("/health/ready")
def readiness_probe():
    return {
        "status": "ready", 
        "market_data": market_data.is_connected,
        "redis": scanner_service.r.ping() if scanner_service.r else False
    }

@app.get("/health/market")
def market_health():
    return {"connected": market_data.is_connected, "source": "yfinance"}

@app.post("/api/alert/create", response_model=AlertResponse)
async def create_alert(query: AlertQuery, db: Session = Depends(get_db)):
    """
    Endpoint to process natural language alert requests.
    This connects to the AI Agent (Clarification Loop).
    """
    # Rate Limit Check
    tier = get_user_tier(query.user_id, db)
    if not custom_limiter.is_allowed(query.user_id, tier):
        raise HTTPException(status_code=429, detail="Daily rate limit exceeded. Upgrade to Pro/Premium for more.")

    # Instantiate the Chutes AI interpreter
    ai = AIAlertInterpreter()
    
    result = await ai.interpret(query.query)

# --- SUBSCRIPTION ENDPOINTS ---
@app.get("/api/subscription/status")
def get_subscription_status(user_id: str, db: Session = Depends(get_db)):
    """Get User Tier and Usage Stats."""
    from app.core.rate_limiter import TIER_QUOTAS
    
    tier = get_user_tier(user_id, db)
    usage = custom_limiter.get_usage(user_id)
    
    # Parse limit from string "100/day" -> 100
    limit_str = TIER_QUOTAS.get(tier, "10/day")
    limit = int(limit_str.split("/")[0])
    
    return {
        "tier": tier,
        "usage": usage,
        "limit": limit,
        "reset_in": "24h" # Simplification
    }

class UpgradeRequest(BaseModel):
    user_id: str
    tier: str # PRO, PREMIUM

@app.post("/api/subscription/upgrade")
def upgrade_subscription(payload: UpgradeRequest, db: Session = Depends(get_db)):
    """Mock Endpoint to Upgrade User."""
    from app.core.subscription import upgrade_user
    
    if payload.tier not in ["FREE", "PRO", "PREMIUM"]:
         raise HTTPException(status_code=400, detail="Invalid Tier")
         
    success = upgrade_user(payload.user_id, payload.tier, db)
    if success:
        return {"success": True, "message": f"Upgraded to {payload.tier}!"}
    return {"success": False, "message": "User not found."}

class RedeemRequest(BaseModel):
    user_id: str
    code: str

@app.post("/api/subscription/redeem")
def redeem_tester_code(payload: RedeemRequest, db: Session = Depends(get_db)):
    """Upgrade user to ADMIN if correct tester code is provided."""
    import hashlib
    from app.core.subscription import upgrade_user
    
    secret_code = os.getenv("TESTER_ACCESS_CODE")
    if not secret_code:
        raise HTTPException(status_code=500, detail="Tester code not configured on server.")
    
    # Secure hash comparison - never log the actual codes
    provided_hash = hashlib.sha256(payload.code.strip().encode()).hexdigest()
    stored_hash = hashlib.sha256(secret_code.encode()).hexdigest()
    
    if provided_hash == stored_hash:
        # Upgrade to ADMIN
        success = upgrade_user(payload.user_id, "ADMIN", db)
        if success:
             return {"success": True, "message": "Access Granted! You are now an Admin."}
        return {"success": False, "message": "User not found."}
    else:
        # Don't reveal whether code was wrong (timing attack prevention)
        return {"success": False, "message": "Invalid Access Code."}


    
    # Map the AI result to our response model
    if result.get("status") == "ERROR":
        return {
            "success": False,
            "status": "ERROR",
            "message": result.get("message", "Unknown error")
        }
    
    if result.get("status") == "NEEDS_CLARIFICATION":
        return {
            "success": False,
            "status": "NEEDS_CLARIFICATION",
            "question": result.get("clarification_question"),
            "missing_info": result.get("missing_info", [])
        }
    
    
    if result.get("status") == "CONFIRMED":
        intent = result.get("intent", "CREATE_ALERT")
        
        # --- HANDLE ALERTS ---
        if intent == "CREATE_ALERT":
            config = result.get("config", {})
            try:
                # We assume single condition for MVP, or take the first one
                conditions = config.get("conditions", [])
                if conditions:
                    cond = conditions[0]
                    new_alert = Alert(
                        user_id=int(query.user_id),
                        symbol=config.get("symbol"),
                        indicator=cond.get("type"),
                        operator=cond.get("operator"),
                        threshold=float(cond.get("value")),
                        status="ACTIVE"
                    )
                    db.add(new_alert)
                    db.commit()
                    db.refresh(new_alert)
                    return {
                        "success": True,
                        "status": "CREATED",
                        "config": config,
                        "message": f"✅ Alert Saved for {config.get('symbol')}! ID: {new_alert.id}"
                    }
                else:
                     return {"success": False, "status": "ERROR", "message": "No conditions found."}
            except Exception as e:
                return {"success": False, "status": "ERROR", "message": f"Database Error: {str(e)}"}

        # --- HANDLE PORTFOLIO ADD ---
        elif intent == "ADD_PORTFOLIO":
            data = result.get("data", {})
            from app.db.models import Portfolio
            from dateutil import parser
            
            items = data.get("items", [])
            if not items and "symbol" in data:
                # Fallback for single item structure
                items = [data]
            
            if not items:
                 return {"success": False, "status": "ERROR", "message": "No valid items found to add."}

            added_msgs = []
            
           try:
                for item in items:
                    # Validate inputs before processing
                    from app.core.security import validate_portfolio_input
                    
                    symbol = item.get("symbol", "")
                    quantity = int(item.get("quantity", 0))
                    price = float(item.get("price", 0.0))
                    
                    is_valid, error_msg = validate_portfolio_input(symbol, quantity, price)
                    if not is_valid:
                        return {"success": False, "status": "ERROR", "message": f"Validation error for {symbol}: {error_msg}"}
                    
                    # Parse date if provided, else Default to Now
                    date_str = item.get("date")
                    if date_str:
                        try:
                            p_date = parser.parse(date_str)
                        except:
                            p_date = datetime.utcnow()
                    else:
                        p_date = datetime.utcnow()

                    new_entry = Portfolio(
                        user_id=int(query.user_id),
                        symbol=symbol,
                        quantity=quantity,
                        avg_price=price,
                        purchase_date=p_date
                    )
                    db.add(new_entry)
                    
                    # Log Trade History (BUY)
                    new_trade = TradeHistory(
                        user_id=int(query.user_id),
                        symbol=item.get("symbol"),
                        quantity=int(item.get("quantity", 0)),
                        price=float(item.get("price", 0.0)),
                        trade_type="BUY",
                        trade_date=p_date
                    )
                    db.add(new_trade)
                    
                    added_msgs.append(f"{new_entry.quantity} {new_entry.symbol}")
                
                db.commit()
                
                # Format date for display
                msg_str = ", ".join(added_msgs)
                return {
                    "success": True, 
                    "status": "PORTFOLIO_ADDED",
                    "message": f"💼 Added: {msg_str}!"
                }
            except Exception as e:
                return {"success": False, "status": "ERROR", "message": f"Portfolio DB Error: {str(e)}"}

        # --- HANDLE PORTFOLIO SELL ---
        elif intent == "SELL_PORTFOLIO":
            data = result.get("data", {})
            sym = data.get("symbol")
            qty_to_sell = int(data.get("quantity", 0))
            sell_price = float(data.get("price", 0.0))
            
            if not sym or qty_to_sell <= 0:
                 return {"success": False, "status": "ERROR", "message": "Invalid sell details."}

            from app.db.models import Portfolio
            
            try:
                # Fetch existing holdings sorted by date (FIFO)
                holdings = db.query(Portfolio).filter(
                    Portfolio.user_id == int(query.user_id),
                    Portfolio.symbol == sym
                ).order_by(Portfolio.purchase_date.asc()).all()
                
                total_qty = sum(h.quantity for h in holdings)
                if total_qty < qty_to_sell:
                    return {"success": False, "status": "ERROR", "message": f"Insufficient holdings. You only have {total_qty} {sym}."}
                
                qty_remaining = qty_to_sell
                total_realized_pnl = 0.0
                
                for h in holdings:
                    if qty_remaining <= 0: break
                    
                    qty_deduct = min(h.quantity, qty_remaining)
                    
                    # Calculate PnL for this portion
                    buy_val = qty_deduct * h.avg_price
                    sell_val = qty_deduct * sell_price
                    pnl = sell_val - buy_val
                    total_realized_pnl += pnl
                    
                    # Update Holding
                    if h.quantity == qty_deduct:
                        db.delete(h)
                    else:
                        h.quantity -= qty_deduct
                    
                    qty_remaining -= qty_deduct
                    
                # Record Trade
                trade = TradeHistory(
                    user_id=int(query.user_id),
                    symbol=sym,
                    quantity=qty_to_sell,
                    price=sell_price,
                    trade_type="SELL",
                    realized_pnl=total_realized_pnl
                )
                db.add(trade)
                db.commit()
                
                pnl_emoji = "🟢" if total_realized_pnl >= 0 else "🔴"
                return {
                    "success": True, 
                    "status": "PORTFOLIO_SOLD", 
                    "message": f"💸 Sold {qty_to_sell} {sym} @ {sell_price}\nRealized P&L: {pnl_emoji} {round(total_realized_pnl, 2)}"
                }
            except Exception as e:
                return {"success": False, "status": "ERROR", "message": f"Sell Error: {str(e)}"}

        # --- HANDLE PORTFOLIO DELETE ---
        elif intent == "DELETE_PORTFOLIO":
            data = result.get("data", {})
            sym = data.get("symbol")
            if not sym:
                 return {"success": False, "status": "ERROR", "message": "Symbol missing for deletion."}
            
            from app.db.models import Portfolio
            try:
                # Delete all entries for this symbol
                deleted_count = db.query(Portfolio).filter(
                    Portfolio.user_id == int(query.user_id),
                    Portfolio.symbol == sym
                ).delete()
                db.commit()
                
                if deleted_count > 0:
                    return {"success": True, "status": "PORTFOLIO_DELETED", "message": f"🗑️ Deleted {deleted_count} entries for {sym}."}
                else:
                    return {"success": False, "status": "ERROR", "message": f"No {sym} found in your portfolio."}
            except Exception as e:
                return {"success": False, "status": "ERROR", "message": f"Delete Error: {str(e)}"}

        # --- HANDLE PORTFOLIO UPDATE ---
        elif intent == "UPDATE_PORTFOLIO":
            data = result.get("data", {})
            sym = data.get("symbol")
            qty = data.get("quantity")
            price = data.get("price")
            
            from app.db.models import Portfolio
            try:
                # Find entries
                entries = db.query(Portfolio).filter(
                    Portfolio.user_id == int(query.user_id),
                    Portfolio.symbol == sym
                ).all()
                
                if not entries:
                    return {"success": False, "status": "ERROR", "message": f"No {sym} found to update."}
                
                # Update Logic: Update ALL entries for this symbol (Simplification)
                # In a real app, we'd ask which specific lot to update.
                count = 0
                for entry in entries:
                    if qty is not None: entry.quantity = int(qty)
                    if price is not None: entry.avg_price = float(price)
                    count += 1
                
                db.commit()
                return {"success": True, "status": "PORTFOLIO_UPDATED", "message": f"📝 Updated {count} entries for {sym}."}

            except Exception as e:
                 return {"success": False, "status": "ERROR", "message": f"Update Error: {str(e)}"}

        # --- HANDLE VIEW PORTFOLIO ---
        elif intent == "VIEW_PORTFOLIO":
            # Just return a signal, Bot will fetch details via another endpoint if needed
            # For MVP, we can fetch here or let bot call /api/portfolio
            return {
                "success": True,
                "status": "VIEW_PORTFOLIO_REQ",
                "intent": "VIEW_PORTFOLIO",
                "message": "Fetching your portfolio..."
            }
            
        # --- HANDLE CHECK PRICE ---
        elif intent == "CHECK_PRICE":
            return {
                "success": True,
                "status": "CONFIRMED",
                "intent": "CHECK_PRICE",
                "data": result.get("data")
            }

    if result.get("status") == "REJECTED":
        return {
            "success": False, # Technical success, but logical rejection
            "status": "REJECTED",
            "message": result.get("message", "I only focus on stock alerts.")
        }

    return {
        "success": False,
        "status": "ERROR",
        "message": "Unexpected AI response format"
    }

@app.get("/api/portfolio/list")
def get_portfolio(user_id: int, db: Session = Depends(get_db)):
    from app.db.models import Portfolio
    
    # Fetch all raw entries
    raw_holdings = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
    
    # Aggregate by Symbol
    portfolio_map = {}
    
    for h in raw_holdings:
        sym = h.symbol
        if sym not in portfolio_map:
            portfolio_map[sym] = {
                "symbol": sym,
                "quantity": 0,
                "total_invested": 0.0,
                "entries": []
            }
        
        portfolio_map[sym]["quantity"] += h.quantity
        portfolio_map[sym]["total_invested"] += (h.quantity * h.avg_price)
        portfolio_map[sym]["entries"].append({
            "qty": h.quantity, 
            "price": h.avg_price, 
            "date": h.purchase_date
        })

    # Enrich with Real-Time Data
    enriched_holdings = []
    total_portfolio_value = 0.0
    total_invested_value = 0.0

    for sym, data in portfolio_map.items():
        qty = data["quantity"]
        invested = data["total_invested"]
        avg_price = invested / qty if qty > 0 else 0.0
        
        # Fetch LTP
        quote = market_data.get_quote(sym)
        ltp = quote.get("ltp") if quote else avg_price # Fallback to avg_price if offline
        prev_close = quote.get("close", ltp) if quote else ltp
        high = quote.get("high", 0) if quote else 0
        low = quote.get("low", 0) if quote else 0

        current_val = qty * ltp
        pnl = current_val - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0.0
        
        # Day Stats
        day_change = ltp - prev_close
        day_change_pct = (day_change / prev_close * 100) if prev_close > 0 else 0.0
        day_pnl = day_change * qty

        total_portfolio_value += current_val
        total_invested_value += invested

        enriched_holdings.append({
            "symbol": sym,
            "quantity": qty,
            "avg_price": round(avg_price, 2),
            "ltp": ltp,
            "current_value": round(current_val, 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round(pnl_pct, 2),
            "invested": round(invested, 2),
            "day_change": round(day_change, 2),
            "day_change_percent": round(day_change_pct, 2),
            "day_pnl": round(day_pnl, 2),
            "high": high,
            "low": low
        })

    # Summary Stats
    total_pnl = total_portfolio_value - total_invested_value
    total_pnl_pct = (total_pnl / total_invested_value * 100) if total_invested_value > 0 else 0.0

    return {
        "user_id": user_id,
        "summary": {
            "total_value": round(total_portfolio_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round(total_pnl_pct, 2)
        },
        "holdings": enriched_holdings
    }

@app.get("/api/portfolio/performance")
def get_portfolio_performance(user_id: int, db: Session = Depends(get_db)):
    """
    Returns the daily total portfolio value for the last 30 days.
    (MVP Assumption: Current holdings were held for the entire period)
    """
    from app.db.models import Portfolio
    import pandas as pd
    
    # 1. Fetch current holdings
    holdings = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
    if not holdings:
        return {"dates": [], "values": []}

    # Aggregate quantities by symbol
    portfolio_qty = {}
    for h in holdings:
        portfolio_qty[h.symbol] = portfolio_qty.get(h.symbol, 0) + h.quantity

    # 2. Batch Fetch History (Optimized with yf.download)
    symbols = list(portfolio_qty.keys())
    if not symbols:
        return {"dates": [], "values": []}

    try:
        import yfinance as yf
        tickers_str = " ".join([f"{s}.NS" for s in symbols])
        # Fetch 1mo history
        data = yf.download(tickers_str, period="1mo", threads=True, group_by='ticker')
        
        # 3. Aggregate Daily Values
        # Structure: Date -> Total Value
        daily_totals = {}
        
        # Iterate over each stock to sum up value
        for sym in symbols:
            qty = portfolio_qty[sym]
            try:
                # Handle single vs multiple ticker return structure
                if len(symbols) == 1:
                    hist = data
                else:
                    hist = data[f"{sym}.NS"]
                
                if not hist.empty:
                    # Normalized Closes
                    closes = hist['Close']
                    for date, price in closes.items():
                        date_str = date.strftime("%Y-%m-%d")
                        value = float(price) * qty
                        daily_totals[date_str] = daily_totals.get(date_str, 0.0) + value
            except Exception as e:
                # print(f"Error processing history for {sym}: {e}")
                pass

        # 4. Format for Chart
        sorted_dates = sorted(daily_totals.keys())
        result_values = [round(daily_totals[d], 2) for d in sorted_dates]
        
        return {
            "dates": sorted_dates,
            "values": result_values
        }

    except Exception as e:
        print(f"Performance API Error: {e}")
        return {"dates": [], "values": []}
