from fastapi import FastAPI, HTTPException, Depends
import logging
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*Timestamp.utcnow.*")
from pydantic import BaseModel
import os
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

# Core Modules
from app.core.ai import AIAlertInterpreter
from app.db.base import Base, engine, get_db, verify_db_connection
from app.db.models import Alert, TradeHistory

from app.core.market_data import MarketDataService
from app.core.scanner import MarketScannerService
from app.core.scheduler import AlertMonitor
from app.core.rate_limiter import custom_limiter
from app.core.subscription import get_user_tier
from app.core.breakout_engine import BreakoutEngine
from app.core.alert_dispatcher import AlertDispatcher
from app.core.scanner_engine import ScannerEngine

# Initialize Database Tables
# Base.metadata.create_all(bind=engine) <- MOVED TO STARTUP EVENT


app = FastAPI(title="AI Intelligent Alert System")
# Last rebuild: 2026-01-11 09:28 IST

# --- API KEY AUTHENTICATION ---
# SECURITY: All API endpoints require a valid API key from the bot
# Authentication is enforced by APIKeyAuthMiddleware (global middleware)
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")


# Security Middleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Maximum request body size (1MB)
MAX_REQUEST_SIZE = 1 * 1024 * 1024


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        # Content Security Policy - restrictive since this is an API
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Prevent caching of sensitive data
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """SECURITY: Limit request body size to prevent DoS attacks."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_REQUEST_SIZE:
                    return Response(
                        content='{"detail": "Request body too large"}',
                        status_code=413,
                        media_type="application/json",
                    )
            except ValueError:
                pass
        return await call_next(request)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    SECURITY: Enforce API key authentication on all non-health endpoints.
    This is a global middleware that protects ALL API routes.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip health check endpoints (needed for Railway/K8s probes)
        if request.url.path.startswith("/health") or request.url.path == "/":
            return await call_next(request)

        # Skip OpenAPI docs endpoints
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # FAIL SECURE: Require API key to be configured in production
        if not API_SECRET_KEY:
            logging.error("SECURITY: API_SECRET_KEY not configured - rejecting request")
            return Response(
                content='{"detail": "Server misconfiguration: Authentication not configured"}',
                status_code=500,
                media_type="application/json",
            )

        # Check for API key in header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return Response(
                content='{"detail": "Missing X-API-Key header"}',
                status_code=401,
                media_type="application/json",
            )

        # Timing-safe comparison
        from app.core.security import secure_compare

        if not secure_compare(api_key, API_SECRET_KEY):
            return Response(
                content='{"detail": "Invalid API key"}',
                status_code=403,
                media_type="application/json",
            )

        return await call_next(request)


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(APIKeyAuthMiddleware)

# CORS - Configured for production
# SECURITY: No origins allowed by default - must be explicitly configured
# For Railway: Set ALLOWED_ORIGINS environment variable
origin_str = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = (
    [o.strip() for o in origin_str.split(",") if o.strip()] if origin_str else []
)

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

# Initialize Engines
alert_dispatcher = AlertDispatcher()
breakout_engine = BreakoutEngine(dispatcher=alert_dispatcher)
# scanner_engine = ScannerEngine(db) # Needs DB session, will init in dependency or startup


# Startup event is defined later after all route definitions (line ~338)


@app.get("/api/quote/{symbol}")
async def get_quote(symbol: str):
    """Fetches live quote for a symbol."""
    # Input Validation
    from app.core.security import validate_symbol
    
    # Sanitize: Remove spaces (TATA STEEL -> TATASTEEL)
    clean_symbol = symbol.upper().replace(" ", "")

    if not validate_symbol(clean_symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol format")

    quote = market_data.get_quote(clean_symbol)
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
    from app.core.security import (
        sanitize_string,
        sanitize_error_message,
        validate_user_id,
    )

    # SECURITY: Validate telegram_id
    is_valid, validated_id = validate_user_id(payload.telegram_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    try:
        # SECURITY: Sanitize input strings
        safe_username = (
            sanitize_string(payload.username, max_length=255)
            if payload.username
            else None
        )
        safe_first_name = (
            sanitize_string(payload.first_name, max_length=255)
            if payload.first_name
            else None
        )
        safe_last_name = (
            sanitize_string(payload.last_name, max_length=255)
            if payload.last_name
            else None
        )

        # Check if user exists
        user = db.query(User).filter(User.telegram_id == validated_id).first()

        if not user:
            # Create new
            user = User(
                telegram_id=validated_id,
                username=safe_username,
                first_name=safe_first_name,
                last_name=safe_last_name,
            )

            # Check for Admin Override
            admin_ids = os.getenv("ADMIN_IDS", "").split(",")
            if str(validated_id) in admin_ids:
                user.subscription_tier = "ADMIN"

            db.add(user)
            db.commit()
            return {
                "success": True,
                "message": "User Registered",
                "user_id": user.telegram_id,
                "is_new": True,
            }
        else:
            # Update existing
            if safe_username:
                user.username = safe_username
            if safe_first_name:
                user.first_name = safe_first_name
            if safe_last_name:
                user.last_name = safe_last_name

            # Re-check Admin (in case added to env later)
            admin_ids = os.getenv("ADMIN_IDS", "").split(",")
            if str(validated_id) in admin_ids and user.subscription_tier != "ADMIN":
                user.subscription_tier = "ADMIN"

            db.commit()
            return {
                "success": True,
                "message": "User Updated",
                "user_id": user.telegram_id,
                "is_new": False,
            }

    except Exception as e:
        # SECURITY: Don't expose internal error details
        logging.error(f"Registration error: {type(e).__name__}")
        return {"success": False, "message": sanitize_error_message(e)}


class AlertQuery(BaseModel):
    user_id: str
    query: str
    context: Optional[Dict[str, Any]] = None


@app.post("/api/screener/custom")
async def custom_screen(
    query_payload: AlertQuery, db: Session = Depends(get_db)
):  # Re-using AlertQuery {user_id, query}
    """
    1. Parse NL Query -> JSON Filters
    2. Fetch Redis Snapshot
    3. Filter Data
    """
    # SECURITY: Input Validation
    from app.core.security import sanitize_query, validate_user_id

    # Validate user_id
    is_valid, validated_user_id = validate_user_id(query_payload.user_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    sanitized_query = sanitize_query(query_payload.query)
    if not sanitized_query:
        raise HTTPException(
            status_code=400,
            detail="Invalid query: too short or contains unsafe characters",
        )

    # Rate Limit Check - use validated user_id
    tier = get_user_tier(str(validated_user_id), db)
    if not custom_limiter.is_allowed(str(validated_user_id), tier):
        raise HTTPException(
            status_code=429,
            detail="Daily rate limit exceeded. Upgrade to Pro/Premium for more.",
        )

    user_query = sanitized_query  # Use sanitized query

    # 1. AI Parse
    ai = AIAlertInterpreter()
    parsed = await ai.parse_screener_query(user_query)

    if "error" in parsed:
        error_message = parsed.get("message", "Could not understand query. Please try: 'Stocks with high volume and RSI below 30'")
        return {"success": False, "message": error_message}

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
        if not item:
            continue

        try:
            # Helper to sanitize floats
            def sanitize(val):
                try:
                    f = float(val)
                    import math
                    if math.isnan(f) or math.isinf(f):
                        return 0.0
                    return f
                except:
                    return 0.0

            # Convert Redis Map to Float
            ltp = sanitize(item.get("ltp", 0))
            change = sanitize(item.get("change_percent", 0))
            volume = sanitize(item.get("volume", 0))
            rsi = sanitize(item.get("rsi", 50))
            pct_52w = sanitize(item.get("pct_from_52w_high", -100))

            match = True
            for f in filters:
                field = f["field"]
                op = f["op"]
                val = f["value"]

                # Check mapping (ltp, volume, etc)
                data_val = 0.0
                if field == "ltp":
                    data_val = ltp
                elif field == "change_pct":
                    data_val = change
                elif field == "volume":
                    data_val = volume
                elif field == "rsi":
                    data_val = rsi
                elif field == "pct_from_52w_high":
                    data_val = pct_52w

                if op == "gt" and not (data_val > val):
                    match = False
                elif op == "lt" and not (data_val < val):
                    match = False
                elif op == "eq" and not (data_val == val):
                    match = False

            if match:
                results.append(
                    {
                        "symbol": item.get("symbol"),
                        "ltp": ltp,
                        "change_percent": change,
                        "timestamp": item.get("timestamp", "Just now"),
                        "match_reason": "AI Match",
                    }
                )
        except Exception as e:
            logging.debug(f"Screen match error: {e}")
            continue

    return {
        "success": True,
        "count": len(results),
        "data": results,
        "filters_used": filters,
    }


@app.get("/api/screener/prebuilt")
async def prebuilt_screen(scan_type: str):
    """
    Execute popular pre-defined scans.
    Falls back to on-demand fetching if Redis cache is empty.
    """

    # Define Criteria
    # 1. Breakout: > 4% Change
    # 2. Volume: Volume > 2.5x Average Volume
    # 3. Value: RSI < 35

    symbols = scanner_service.symbols
    pipe = scanner_service.r.pipeline()
    for sym in symbols:
        pipe.hgetall(f"stock:{sym}")
    data_list = pipe.execute()

    # Check if Redis is empty (first request after startup)
    non_empty_count = sum(1 for item in data_list if item)

    if non_empty_count < 5:  # Less than 5 stocks in Redis = not ready
        # Fallback: Fetch on-demand using historical data
        import yfinance as yf
        import logging

        logger = logging.getLogger(__name__)
        logger.info("🔄 Redis cache empty, fetching historical data for scanner...")

        data_list = []
        # Fetch data for all symbols

        for sym in symbols:
            try:
                # Fetch last 5 days to get at least 2 trading days
                ticker = yf.Ticker(f"{sym}.NS")
                hist = ticker.history(period="5d")

                if len(hist) >= 2:
                    # Get last 2 trading days
                    last_day = hist.iloc[-1]
                    prev_day = hist.iloc[-2]

                    # Calculate change from previous close
                    ltp = float(last_day["Close"])
                    prev_close = float(prev_day["Close"])
                    change_pct = ((ltp - prev_close) / prev_close) * 100

                    # Get 10-day average volume
                    avg_volume = hist["Volume"].mean() if len(hist) > 0 else 500000

                    data_list.append(
                        {
                            "symbol": sym,
                            "ltp": str(ltp),
                            "change_percent": str(round(change_pct, 2)),
                            "volume": str(int(last_day["Volume"])),
                            "rsi": "50",  # Default RSI
                            "avg_volume": str(int(avg_volume)),
                            "timestamp": str(hist.index[-1].date()),
                        }
                    )
                else:
                    # Not enough data
                    continue

            except Exception as e:
                logger.debug(f"Skipping {sym}: {e}")
                continue

    results = []
    for item in data_list:
        if not item:
            continue
        try:
            ltp = float(item.get("ltp", 0))
            change = float(item.get("change_percent", 0))
            volume = float(item.get("volume", 0))
            rsi_val = item.get("rsi", 50)

            # Handle Infinity/NaN values that might be in Redis from old calculations
            if rsi_val == "inf" or rsi_val == "Infinity" or rsi_val == "-inf":
                rsi = 50.0  # Default neutral value
            else:
                rsi = float(rsi_val)
                # Handle actual infinity float values
                if rsi == float('inf') or rsi == float('-inf'):
                    rsi = 50.0

            match = False

            if scan_type == "scan_breakout":
                # Lowered threshold: >1.5% change (was 4%)
                if abs(change) > 1.5:
                    match = True

            elif scan_type == "scan_volume":
                avg_vol = float(item.get("avg_volume", 1_000_000))
                # Lowered threshold: Volume > 1.2x Average (was 2.5x)
                if volume > (avg_vol * 1.2):
                    match = True

            elif scan_type == "scan_value":
                if rsi < 35.0:
                    match = True

            if match:
                # Clean Data types for JSON response
                cleaned_item = {
                    "symbol": item.get("symbol"),
                    "ltp": ltp,
                    "change_percent": change,
                    "volume": int(volume),
                    "rsi": rsi,
                    "timestamp": item.get("timestamp", "Just now"),
                }
                results.append(cleaned_item)

        except Exception as e:
            logging.debug(f"Prebuilt screen error: {e}")
            continue

    # Sort results
    if scan_type == "scan_breakout":
        results.sort(key=lambda x: float(x.get("change_percent", 0)), reverse=True)
    elif scan_type == "scan_value":
        results.sort(key=lambda x: float(x.get("rsi", 50)))

    return {"success": True, "count": len(results), "data": results}


@app.get("/api/screener/guru")
async def guru_screen(guru: str):
    """
    Execute guru-inspired screeners.
    guru: 'minervini', 'lynch', 'buffett'
    """
    from app.core.fundamentals import apply_guru_filter, GURU_SCREENERS

    if guru not in GURU_SCREENERS:
        return {
            "success": False,
            "error": f"Unknown guru: {guru}. Available: {list(GURU_SCREENERS.keys())}",
        }

    symbols = scanner_service.symbols
    pipe = scanner_service.r.pipeline()
    for sym in symbols:
        pipe.hgetall(f"stock:{sym}")
    data_list = pipe.execute()

    results = []
    for i, item in enumerate(data_list):
        if not item:
            continue
        try:
            item["symbol"] = symbols[i]

            # Apply guru filter
            if apply_guru_filter(item, guru):
                ltp = float(item.get("ltp", 0))
                pe = float(item.get("pe", 0))
                roe = float(item.get("roe", 0))
                high_52w = float(item.get("high_52w", 0))

                results.append(
                    {
                        "symbol": item.get("symbol"),
                        "ltp": ltp,
                        "pe": round(pe, 2),
                        "roe": round(roe, 2),
                        "high_52w": high_52w,
                        "pct_from_high": round(((high_52w - ltp) / high_52w) * 100, 1)
                        if high_52w > 0
                        else 0,
                        "rsi": float(item.get("rsi", 50)),
                        "timestamp": item.get("timestamp", "Today"),
                    }
                )
        except Exception as e:
            logging.debug(f"Guru screen error: {e}")
            continue

    # Sort by best matches
    if guru == "minervini":
        results.sort(key=lambda x: x.get("pct_from_high", 100))  # Closest to 52w high
    elif guru in ["lynch", "buffett"]:
        results.sort(key=lambda x: x.get("pe", 999))  # Lowest P/E first

    guru_info = GURU_SCREENERS[guru]
    return {
        "success": True,
        "guru": guru_info["name"],
        "description": guru_info["description"],
        "count": len(results),
        "data": results,
    }


class SaveScanRequest(BaseModel):
    user_id: str
    name: str
    query: str


@app.post("/api/screener/save")
def save_scan(payload: SaveScanRequest, db: Session = Depends(get_db)):
    """Save a custom query."""
    from app.core.security import (
        validate_user_id,
        sanitize_string,
        sanitize_error_message,
    )

    # SECURITY: Validate user_id
    is_valid, validated_user_id = validate_user_id(payload.user_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    # SECURITY: Sanitize inputs
    safe_name = sanitize_string(payload.name, max_length=100)
    safe_query = sanitize_string(payload.query, max_length=500)

    if not safe_name or len(safe_name) < 1:
        raise HTTPException(status_code=400, detail="Invalid scan name")

    try:
        from app.db.models import SavedScan

        new_scan = SavedScan(
            user_id=validated_user_id, name=safe_name, query=safe_query
        )
        db.add(new_scan)
        db.commit()
        return {"success": True, "message": f"Saved '{safe_name}'!"}
    except Exception as e:
        logging.error(f"Save scan error: {type(e).__name__}")
        return {"success": False, "message": sanitize_error_message(e)}


@app.get("/api/screener/saved")
def list_saved_scans(user_id: str, db: Session = Depends(get_db)):
    """List saved scans for a user."""
    from app.core.security import validate_user_id, sanitize_error_message

    # SECURITY: Validate user_id
    is_valid, validated_user_id = validate_user_id(user_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    try:
        from app.db.models import SavedScan

        scans = db.query(SavedScan).filter(SavedScan.user_id == validated_user_id).all()
        return {
            "success": True,
            "data": [{"id": s.id, "name": s.name, "query": s.query} for s in scans],
        }
    except Exception as e:
        logging.error(f"List saved scans error: {type(e).__name__}")
        return {"success": False, "message": sanitize_error_message(e)}


@app.delete("/api/screener/saved/{scan_id}")
def delete_saved_scan(scan_id: int, user_id: str, db: Session = Depends(get_db)):
    """Delete a saved scan."""
    from app.core.security import validate_user_id, sanitize_error_message

    # SECURITY: Validate user_id
    is_valid, validated_user_id = validate_user_id(user_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    try:
        from app.db.models import SavedScan

        # SECURITY: Ensure user can only delete their own scans (IDOR protection)
        deleted_count = (
            db.query(SavedScan)
            .filter(SavedScan.id == scan_id, SavedScan.user_id == validated_user_id)
            .delete()
        )
        db.commit()

        if deleted_count == 0:
            return {"success": False, "message": "Scan not found or access denied."}

        return {"success": True, "message": "Scan deleted."}
    except Exception as e:
        logging.error(f"Delete scan error: {type(e).__name__}")
        return {"success": False, "message": "An error occurred. Please try again."}


class FeedbackRequest(BaseModel):
    user_id: str
    category: str  # ISSUE or FEEDBACK
    message: str


from fastapi import BackgroundTasks

@app.get("/api/test/email")
def test_email_endpoint():
    """Test email sending - DEBUG ONLY. Remove in production."""
    import os
    from datetime import datetime
    
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    admin_email = os.getenv("ADMIN_EMAIL")
    
    config = {
        "smtp_server": os.getenv("SMTP_SERVER", "NOT SET"),
        "smtp_port": os.getenv("SMTP_PORT", "NOT SET"),
        "smtp_username": "SET" if smtp_user else "NOT SET",
        "smtp_password": "SET" if smtp_pass else "NOT SET",
        "admin_email": admin_email or "NOT SET",
    }
    
    if not smtp_user or not smtp_pass:
        return {"success": False, "error": "Missing SMTP credentials", "config": config}
    
    try:
        from app.core.email_utils import send_email_sync
        
        subject = f"Pystock Test Email - {datetime.utcnow()}"
        body = f"This is a test email sent from Railway at {datetime.utcnow()}"
        
        # Call synchronously to capture errors
        send_email_sync(subject, body, admin_email)
        
        return {"success": True, "message": f"Email sent to {admin_email}", "config": config}
    except Exception as e:
        return {"success": False, "error": str(e), "config": config}

@app.post("/api/support/submit")
def submit_feedback(payload: FeedbackRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Submit user feedback or issue."""
    from datetime import datetime
    from app.core.security import validate_user_id, sanitize_string, sanitize_error_message
    
    # SECURITY: Validate user_id
    is_valid, validated_user_id = validate_user_id(payload.user_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    # SECURITY: Sanitize inputs
    safe_category = sanitize_string(payload.category, max_length=20).upper()
    safe_message = sanitize_string(payload.message, max_length=2000)

    if safe_category not in ["ISSUE", "FEEDBACK"]:
        raise HTTPException(status_code=400, detail="Invalid category")

    if not safe_message or len(safe_message) < 5:
        raise HTTPException(status_code=400, detail="Message too short")

    try:
        from app.db.models import UserFeedback, User
        
        # Resolve Telegram ID to Internal User ID
        # validated_user_id is the Telegram ID (BigInt)
        user = db.query(User).filter(User.telegram_id == validated_user_id).first()
        
        internal_user_id = user.id if user else None
        
        # If user not found, we can still save it with NULL user_id or handle gracefully
        # Since user_id is FK and nullable is False (by default without nullable=True), 
        # we might need a fallback. But likely user exists if they are using the bot.
        # If user doesn't exist, we can't save to this table if FK is strict.
        
        if not user:
             # Log warning and maybe return error, or proceed if nullable.
             logging.warning(f"Feedback submitted by unknown user: {validated_user_id}")
             # For now, let's assume strict FK and fail if user not found, as bot user should exist.
             return {"success": False, "message": "User not registered. Please /start first."}

        feedback = UserFeedback(
            user_id=internal_user_id,
            category=safe_category,
            message=safe_message
        )
        db.add(feedback)
        db.commit()
        
        # Log for email routing (simulated)
        # Send Email in Background
        from app.core.email_utils import send_email_background
        
        user_mention = f"@{user.username}" if user and user.username else "N/A"
        
        subject = f"Pystock: New {safe_category} from User {validated_user_id} ({user_mention})"
        body = (
            f"New {safe_category} Received:\n\n"
            f"User ID: {validated_user_id}\n"
            f"Username: {user_mention}\n"
            f"Category: {safe_category}\n"
            f"Time: {datetime.utcnow()}\n\n"
            f"Message:\n{safe_message}\n\n"
            f"--------------------------------\n"
            f"Sent from Pystock Bot Backend"
        )
        
        logging.info(f"📧 ATTEMPTING EMAIL to {user.username if user else 'Unknown'} | Category: {safe_category}")
        send_email_background(background_tasks, subject, body)
        
        # Log for trace
        logging.info(f"📧 EMAIL_QUEUED: {subject}")
        
        return {"success": True, "message": "Feedback received. We will contact you if needed."}
    except Exception as e:
        logging.error(f"Feedback error: {type(e).__name__}")
        return {"success": False, "message": sanitize_error_message(e)}


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
    # CRITICAL: Import at top to avoid UnboundLocalError
    import asyncio
    import threading
    import time
    import os
    from datetime import datetime

    start_time = time.time()
    logger = logging.getLogger("uvicorn")

    logger.info("🚀 Starting backend services...")

    # Check AI Key
    zai_key = os.getenv("ZAI_API_KEY")
    if zai_key:
        masked = f"{zai_key[:5]}...{zai_key[-5:]}" if len(zai_key) > 10 else "Invalid"
        logger.info(f"✅ ZAI_API_KEY found: {masked}")
    else:
        logger.error("❌ ZAI_API_KEY NOT FOUND in environment variables!")

    # Check if market is open (9:15 AM - 3:30 PM IST, weekdays)
    is_market_hours = False
    try:
        import pytz

        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
        is_weekday = now.weekday() < 5  # Mon-Fri
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        is_market_hours = is_weekday and market_open <= now <= market_close
    except Exception as e:
        logger.error(f"⚠️ Timezone init failed: {e}. Defaulting to Market CLOSED.")
        is_market_hours = False

    if is_market_hours:
        logger.info("📈 Market OPEN - Using SmartAPI for real-time data")
    else:
        logger.info("🌙 Market CLOSED - Using yfinance (faster startup)")

    # Initialize SmartAPI only during market hours
    # SmartAPI Removed - Using yfinance only
    logger.info("Using yfinance for all data fetching.")

    # Run Schema Migration Check (DEFER TO BACKGROUND - don't block startup)
    def init_database_background():
        """Initialize DB in background thread - don't block app startup"""
        try:
            logger.info("🔌 Verifying Database Connection...")
            if verify_db_connection(engine):
                logger.info("✅ Database Connection Verified")

                # Create Tables
                logger.info("🛠️ Initializing Database Tables...")
                Base.metadata.create_all(bind=engine)
                logger.info("✅ Database Tables Verified/Created")

                from app.db.migration import check_and_fix_schema

                check_and_fix_schema()
            else:
                logger.error(
                    "❌ Database Connection Failed after retries - API will have limited functionality"
                )
        except Exception as e:
            logger.error(f"❌ Database Init Failed: {e}")

    # Start DB init in background (don't wait for it)
    threading.Thread(target=init_database_background, daemon=True).start()

    # Initialize market data service
    logger.info("Initializing Market Data service...")
    if market_data.login():
        logger.info("✅ Market Data Service Ready")
    else:
        logger.warning("⚠️ Market Data Service failed, using yfinance fallback")

    # Start Scanner Loop (runs in daemon thread)
    scanner_service.start()

    # Start Fundamentals Service (delayed 30s, daemon thread)
    from app.core.fundamentals import FundamentalsService

    fundamentals_service = FundamentalsService(scanner_service.symbols)
    fundamentals_service.start()
    app.state.fundamentals_service = fundamentals_service

    # Start Alert Monitor
    await monitor_service.start()

    # Log startup time
    elapsed = time.time() - start_time
    logger.info(f"🚀 Backend started in {elapsed:.2f}s")

    # Start Railway Keepalive (prevents service sleep - critical for low latency)
    import httpx

    async def keepalive_ping():
        """Ping /health every 4 minutes to prevent Railway sleep"""
        while True:
            try:
                await asyncio.sleep(240)  # 4 minutes
                async with httpx.AsyncClient() as client:
                    await client.get("http://localhost:8000/health", timeout=5)
                logger.debug("🏓 Keepalive ping sent")
            except Exception as e:
                logger.error(f"Keepalive ping failed: {e}")

    # Run keepalive in background
    asyncio.create_task(keepalive_ping())
    logger.info("🏓 Railway keepalive service started (prevents idle sleep)")

    logger.info("🚀 All services started successfully")

    # Run keepalive in background
    asyncio.create_task(keepalive_ping())
    logger.info("🏓 Railway keepalive service started (prevents idle sleep)")

    logger.info("🚀 All services started successfully")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "backend"}


@app.get("/health/ready")
def readiness_probe():
    return {
        "status": "ready",
        "market_data": market_data.is_connected,
        "redis": scanner_service.r.ping() if scanner_service.r else False,
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
    from app.core.security import validate_user_id, sanitize_query

    # SECURITY: Validate user_id
    is_valid, validated_user_id = validate_user_id(query.user_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    # SECURITY: Sanitize query
    sanitized_query = sanitize_query(query.query)
    if not sanitized_query:
        raise HTTPException(status_code=400, detail="Invalid query")

    # Rate Limit Check - use validated user_id
    tier = get_user_tier(str(validated_user_id), db)
    if not custom_limiter.is_allowed(str(validated_user_id), tier):
        raise HTTPException(
            status_code=429,
            detail="Daily rate limit exceeded. Upgrade to Pro/Premium for more.",
        )

    # Instantiate the Chutes AI interpreter
    ai = AIAlertInterpreter()

    # Pass context if available
    result = await ai.interpret(query.query, context=query.context)

    # Map the AI result to our response model
    if result.get("status") == "ERROR":
        return {
            "success": False,
            "status": "ERROR",
            "message": result.get("message", "Unknown error"),
        }

    if result.get("status") == "NEEDS_CLARIFICATION":
        return {
            "success": False,
            "status": "NEEDS_CLARIFICATION",
            "question": result.get("clarification_question"),
            "missing_info": result.get("missing_info", []),
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
                        user_id=validated_user_id,
                        symbol=config.get("symbol"),
                        indicator=cond.get("type"),
                        operator=cond.get("operator"),
                        threshold=float(cond.get("value")),
                        status="ACTIVE",
                    )
                    db.add(new_alert)
                    db.commit()
                    db.refresh(new_alert)
                    return {
                        "success": True,
                        "status": "CREATED",
                        "config": config,
                        "message": f"✅ Alert Saved for {config.get('symbol')}! ID: {new_alert.id}",
                    }
                else:
                    return {
                        "success": False,
                        "status": "ERROR",
                        "message": "No conditions found.",
                    }
            except Exception as e:
                logging.error(f"Alert creation error: {type(e).__name__}")
                return {
                    "success": False,
                    "status": "ERROR",
                    "message": "Database error. Please try again.",
                }

        # --- HANDLE PORTFOLIO ADD ---
        elif intent == "ADD_PORTFOLIO":
            data = result.get("data", {})
            from app.db.models import Portfolio
            from dateutil import parser
            from datetime import datetime

            items = data.get("items", [])
            if not items and "symbol" in data:
                # Fallback for single item structure
                items = [data]

            if not items:
                return {
                    "success": False,
                    "status": "ERROR",
                    "message": "No valid items found to add.",
                }

            added_msgs = []

            try:
                for item in items:
                    # Validate inputs before processing
                    from app.core.security import validate_portfolio_input

                    symbol = item.get("symbol", "")
                    quantity = int(item.get("quantity", 0))
                    price = float(item.get("price", 0.0))

                    is_valid, error_msg = validate_portfolio_input(
                        symbol, quantity, price
                    )
                    if not is_valid:
                        return {
                            "success": False,
                            "status": "ERROR",
                            "message": f"Validation error for {symbol}: {error_msg}",
                        }

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
                        user_id=validated_user_id,
                        symbol=symbol,
                        quantity=quantity,
                        avg_price=price,
                        purchase_date=p_date,
                    )
                    db.add(new_entry)

                    # Log Trade History (BUY)
                    new_trade = TradeHistory(
                        user_id=validated_user_id,
                        symbol=item.get("symbol"),
                        quantity=int(item.get("quantity", 0)),
                        price=float(item.get("price", 0.0)),
                        trade_type="BUY",
                        trade_date=p_date,
                    )
                    db.add(new_trade)

                    added_msgs.append(f"{new_entry.quantity} {new_entry.symbol}")

                db.commit()

                # Format date for display
                msg_str = ", ".join(added_msgs)
                return {
                    "success": True,
                    "status": "PORTFOLIO_ADDED",
                    "message": f"💼 Added: {msg_str}!",
                }
            except Exception as e:
                logging.error(f"Portfolio add error: {type(e).__name__}")
                return {
                    "success": False,
                    "status": "ERROR",
                    "message": "Could not add to portfolio. Please try again.",
                }

        # --- HANDLE PORTFOLIO SELL ---
        elif intent == "SELL_PORTFOLIO":
            data = result.get("data", {})
            sym = data.get("symbol")
            qty_to_sell = int(data.get("quantity", 0))
            sell_price = float(data.get("price", 0.0))

            if not sym or qty_to_sell <= 0:
                return {
                    "success": False,
                    "status": "ERROR",
                    "message": "Invalid sell details.",
                }

            from app.db.models import Portfolio

            try:
                # Fetch existing holdings sorted by date (FIFO)
                holdings = (
                    db.query(Portfolio)
                    .filter(
                        Portfolio.user_id == validated_user_id, Portfolio.symbol == sym
                    )
                    .order_by(Portfolio.purchase_date.asc())
                    .all()
                )

                total_qty = sum(h.quantity for h in holdings)
                if total_qty < qty_to_sell:
                    return {
                        "success": False,
                        "status": "ERROR",
                        "message": f"Insufficient holdings. You only have {total_qty} {sym}.",
                    }

                qty_remaining = qty_to_sell
                total_realized_pnl = 0.0

                for h in holdings:
                    if qty_remaining <= 0:
                        break

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
                    user_id=validated_user_id,
                    symbol=sym,
                    quantity=qty_to_sell,
                    price=sell_price,
                    trade_type="SELL",
                    realized_pnl=total_realized_pnl,
                )
                db.add(trade)
                db.commit()

                pnl_emoji = "🟢" if total_realized_pnl >= 0 else "🔴"
                return {
                    "success": True,
                    "status": "PORTFOLIO_SOLD",
                    "message": f"💸 Sold {qty_to_sell} {sym} @ {sell_price}\nRealized P&L: {pnl_emoji} {round(total_realized_pnl, 2)}",
                }
            except Exception as e:
                logging.error(f"Portfolio sell error: {type(e).__name__}")
                return {
                    "success": False,
                    "status": "ERROR",
                    "message": "Could not process sell. Please try again.",
                }

        # --- HANDLE PORTFOLIO DELETE ---
        elif intent == "DELETE_PORTFOLIO":
            data = result.get("data", {})
            sym = data.get("symbol")
            if not sym:
                return {
                    "success": False,
                    "status": "ERROR",
                    "message": "Symbol missing for deletion.",
                }

            from app.db.models import Portfolio

            try:
                # Delete all entries for this symbol
                deleted_count = (
                    db.query(Portfolio)
                    .filter(
                        Portfolio.user_id == validated_user_id, Portfolio.symbol == sym
                    )
                    .delete()
                )
                db.commit()

                if deleted_count > 0:
                    return {
                        "success": True,
                        "status": "PORTFOLIO_DELETED",
                        "message": f"🗑️ Deleted {deleted_count} entries for {sym}.",
                    }
                else:
                    return {
                        "success": False,
                        "status": "ERROR",
                        "message": f"No {sym} found in your portfolio.",
                    }
            except Exception as e:
                logging.error(f"Portfolio delete error: {type(e).__name__}")
                return {
                    "success": False,
                    "status": "ERROR",
                    "message": "Could not delete. Please try again.",
                }

        # --- HANDLE PORTFOLIO UPDATE ---
        elif intent == "UPDATE_PORTFOLIO":
            data = result.get("data", {})
            sym = data.get("symbol")
            qty = data.get("quantity")
            price = data.get("price")

            from app.db.models import Portfolio

            try:
                # Find entries
                entries = (
                    db.query(Portfolio)
                    .filter(
                        Portfolio.user_id == validated_user_id, Portfolio.symbol == sym
                    )
                    .all()
                )

                if not entries:
                    return {
                        "success": False,
                        "status": "ERROR",
                        "message": f"No {sym} found to update.",
                    }

                # Update Logic: Update ALL entries for this symbol (Simplification)
                # In a real app, we'd ask which specific lot to update.
                count = 0
                for entry in entries:
                    if qty is not None:
                        entry.quantity = int(qty)
                    if price is not None:
                        entry.avg_price = float(price)
                    count += 1

                db.commit()
                return {
                    "success": True,
                    "status": "PORTFOLIO_UPDATED",
                    "message": f"📝 Updated {count} entries for {sym}.",
                }

            except Exception as e:
                logging.error(f"Portfolio update error: {type(e).__name__}")
                return {
                    "success": False,
                    "status": "ERROR",
                    "message": "Could not update. Please try again.",
                }

        # --- HANDLE VIEW PORTFOLIO ---
        elif intent == "VIEW_PORTFOLIO":
            # Just return a signal, Bot will fetch details via another endpoint if needed
            return {
                "success": True,
                "status": "VIEW_PORTFOLIO_REQ",
                "intent": "VIEW_PORTFOLIO",
                "message": "Fetching your portfolio...",
            }

        # --- HANDLE CHECK PRICE ---
        elif intent == "CHECK_PRICE":
            return {
                "success": True,
                "status": "CONFIRMED",
                "intent": "CHECK_PRICE",
                "data": result.get("data"),
            }

        # --- HANDLE CHECK FUNDAMENTALS ---
        elif intent == "CHECK_FUNDAMENTALS":
            symbol = result.get("data", {}).get("symbol")
            if symbol:
                fundamentals = market_data.get_fundamentals(symbol)
                if fundamentals:
                    return {
                        "success": True,
                        "status": "FUNDAMENTALS",
                        "data": fundamentals,
                    }

            return {
                "success": False,
                "status": "ERROR",
                "message": f"Could not fetch fundamentals for {symbol}",
            }

        # --- HANDLE ANALYSIS ---
        elif intent == "ANALYZE_STOCK":
            symbol = result.get("data", {}).get("symbol")
            if symbol:
                return {
                    "success": True,
                    "status": "ANALYZE_STOCK",
                    "symbol": symbol,
                    "data": result.get("data")
                }


    if result.get("status") == "MARKET_INFO":
        return {
            "success": True,
            "status": "MARKET_INFO",
            "message": result.get("data", {}).get("answer", "No info found."),
        }

    if result.get("status") == "REJECTED":
        return {
            "success": False,  # Technical success, but logical rejection
            "status": "REJECTED",
            "message": result.get("message", "I only focus on stock alerts."),
        }

    return {
        "success": False,
        "status": "ERROR",
        "message": "Unexpected AI response format",
    }


@app.get("/api/fundamentals/{symbol}")
async def get_fundamentals(symbol: str):
    """Returns fundamental data for a stock."""
    from app.core.security import validate_symbol
    
    clean_symbol = symbol.upper().replace(" ", "")
    
    if not validate_symbol(clean_symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol")
        
    data = market_data.get_fundamentals(clean_symbol)
    if data:
        return {"success": True, "data": data}
    return {"success": False, "message": "Could not fetch fundamentals."}


@app.get("/api/analyze/{symbol}")
async def analyze_stock(symbol: str):
    """Returns technical analysis of a stock."""
    from app.core.security import validate_symbol
    
    clean_symbol = symbol.upper().replace(" ", "")
    
    if not validate_symbol(clean_symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol")
        
    data = market_data.get_analysis(clean_symbol)
    if data:
        return {"success": True, "data": data}
    return {"success": False, "message": "Could not analyze stock."}


@app.get("/api/chart/{symbol}")
async def get_chart(symbol: str):
    """Returns a base64 encoded chart image."""
    from app.core.charting import generate_stock_chart
    
    clean_symbol = symbol.upper().replace(" ", "")
    chart_base64 = generate_stock_chart(clean_symbol)
    if chart_base64:
        return {"success": True, "image": chart_base64}
    return {"success": False, "message": "Could not generate chart."}


# --- SUBSCRIPTION ENDPOINTS ---
@app.get("/api/subscription/status")
def get_subscription_status(user_id: str, db: Session = Depends(get_db)):
    """Get User Tier and Usage Stats."""
    from app.core.rate_limiter import TIER_QUOTAS
    from app.core.security import validate_user_id

    # SECURITY: Validate user_id
    is_valid, validated_user_id = validate_user_id(user_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    tier = get_user_tier(str(validated_user_id), db)
    usage = custom_limiter.get_usage(str(validated_user_id))

    # Parse limit from string "100/day" -> 100
    limit_str = TIER_QUOTAS.get(tier, "10/day")
    limit = int(limit_str.split("/")[0])

    return {
        "tier": tier,
        "usage": usage,
        "limit": limit,
        "reset_in": "24h",  # Simplification
    }


class UpgradeRequest(BaseModel):
    user_id: str
    tier: str  # PRO, PREMIUM


@app.post("/api/subscription/upgrade")
def upgrade_subscription(payload: UpgradeRequest, db: Session = Depends(get_db)):
    """Mock Endpoint to Upgrade User."""
    from app.core.subscription import upgrade_user
    from app.core.security import validate_user_id

    # SECURITY: Validate user_id
    is_valid, validated_user_id = validate_user_id(payload.user_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if payload.tier not in ["FREE", "PRO", "PREMIUM"]:
        raise HTTPException(status_code=400, detail="Invalid Tier")

    success = upgrade_user(str(validated_user_id), payload.tier, db)
    if success:
        return {"success": True, "message": f"Upgraded to {payload.tier}!"}
    return {"success": False, "message": "User not found."}


class RedeemRequest(BaseModel):
    user_id: str
    code: str
    tier: str = "ADMIN"  # Can be "ADMIN" or "TESTER"


@app.post("/api/subscription/redeem")
def redeem_code(payload: RedeemRequest, db: Session = Depends(get_db)):
    """Upgrade user to ADMIN or TESTER based on code provided."""
    from app.core.subscription import upgrade_user
    from app.core.security import validate_user_id, secure_compare, sanitize_string

    # SECURITY: Validate user_id
    is_valid, validated_user_id = validate_user_id(payload.user_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    # Choose code based on tier
    if payload.tier == "TESTER":
        secret_code = os.getenv("TESTER_CODE")
        tier_name = "TESTER"
    else:
        secret_code = os.getenv("Admin_code")
        tier_name = "ADMIN"

    if not secret_code:
        raise HTTPException(
            status_code=500, detail=f"{tier_name} code not configured on server."
        )

    # SECURITY: Sanitize and use timing-safe comparison
    provided_code = sanitize_string(payload.code, max_length=100).strip()

    if secure_compare(provided_code, secret_code):
        # Upgrade to specified tier
        success = upgrade_user(str(validated_user_id), tier_name, db)
        if success:
            return {
                "success": True,
                "message": f"Access Granted! You are now a {tier_name}.",
            }
        return {"success": False, "message": "User not found."}
    else:
        # Don't reveal whether code was wrong (timing attack prevention)
        return {"success": False, "message": "Invalid Access Code."}


@app.get("/api/portfolio/list")
async def get_portfolio(user_id: int, db: Session = Depends(get_db)):
    from app.db.models import Portfolio
    from app.core.security import validate_user_id

    # SECURITY: Validate user_id
    is_valid, validated_user_id = validate_user_id(user_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    # Fetch all raw entries
    raw_holdings = (
        db.query(Portfolio).filter(Portfolio.user_id == validated_user_id).all()
    )

    # Aggregate by Symbol
    portfolio_map = {}

    for h in raw_holdings:
        sym = h.symbol
        if sym not in portfolio_map:
            portfolio_map[sym] = {
                "symbol": sym,
                "quantity": 0,
                "total_invested": 0.0,
                "entries": [],
            }

        portfolio_map[sym]["quantity"] += h.quantity
        portfolio_map[sym]["total_invested"] += h.quantity * h.avg_price
        portfolio_map[sym]["entries"].append(
            {"qty": h.quantity, "price": h.avg_price, "date": h.purchase_date}
        )

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
        ltp = quote["ltp"] if quote else avg_price  # Fallback

        current_value = qty * ltp
        pnl = current_value - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0.0

        enriched_holdings.append(
            {
                "symbol": sym,
                "quantity": qty,
                "avg_price": round(avg_price, 2),
                "ltp": round(ltp, 2),
                "current_value": round(current_value, 2),
                "invested_value": round(invested, 2),
                "pnl": round(pnl, 2),
                "pnl_percent": round(pnl_pct, 2),
            }
        )

        total_portfolio_value += current_value
        total_invested_value += invested

    total_pnl = total_portfolio_value - total_invested_value
    total_pnl_percent = (
        (total_pnl / total_invested_value * 100) if total_invested_value > 0 else 0.0
    )

    summary = {
        "total_value": round(total_portfolio_value, 2),
        "total_invested": round(total_invested_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_percent": round(total_pnl_percent, 2),
    }

    # --- AI INSIGHT ---
    ai_insight = None
    if raw_holdings:
        try:
            ai = AIAlertInterpreter()
            ai_insight = await ai.generate_portfolio_summary(
                {"summary": summary, "holdings": enriched_holdings}
            )
        except Exception as e:
            # Fallback if AI fails (e.g., token error), so functionality isn't broken
            import logging

            logger = logging.getLogger("uvicorn")
            logger.error(f"AI Summary Error: {e}")
            ai_insight = "AI Insights currently unavailable."

    return {
        "success": True,
        "summary": summary,
        "holdings": enriched_holdings,
        "ai_insight": ai_insight,
    }


@app.get("/api/portfolio/performance")
def get_portfolio_performance(user_id: int, db: Session = Depends(get_db)):
    """
    Returns the daily total portfolio value for the last 30 days.
    (MVP Assumption: Current holdings were held for the entire period)
    """
    from app.db.models import Portfolio
    from app.core.security import validate_user_id
    import pandas as pd

    # SECURITY: Validate user_id
    is_valid, validated_user_id = validate_user_id(user_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    # 1. Fetch current holdings
    holdings = db.query(Portfolio).filter(Portfolio.user_id == validated_user_id).all()
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
        data = yf.download(tickers_str, period="1mo", threads=True, group_by="ticker")

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
                    closes = hist["Close"]
                    for date, price in closes.items():
                        date_str = date.strftime("%Y-%m-%d")
                        value = float(price) * qty
                        daily_totals[date_str] = daily_totals.get(date_str, 0.0) + value
            except Exception as e:
                logging.debug(f"Error processing history for {sym}: {e}")
                pass

        # 4. Format for Chart
        sorted_dates = sorted(daily_totals.keys())
        result_values = [round(daily_totals[d], 2) for d in sorted_dates]

        return {"dates": sorted_dates, "values": result_values}

    except Exception as e:
        print(f"Performance API Error: {e}")
        return {"dates": [], "values": []}
