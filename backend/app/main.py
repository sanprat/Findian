from fastapi import FastAPI, HTTPException, Depends
import logging
from pydantic import BaseModel
import os
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

# Core Modules
from app.core.ai import AIAlertInterpreter 
from app.db.base import Base, engine, get_db
from app.db.models import Alert
from app.core.market_data import MarketDataService

# Initialize Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Intelligent Alert System")
market_data = MarketDataService()

class AlertQuery(BaseModel):
    user_id: str
    query: str

class AlertResponse(BaseModel):
    success: bool
    status: str
    config: Optional[Dict[str, Any]] = None
    question: Optional[str] = None
    missing_info: Optional[List[str]] = None
    message: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    # Attempt login on startup
    logger = logging.getLogger("uvicorn")
    logger.info("Attempting Finvasia Login...")
    if market_data.login():
        logger.info("✅ Connected to Market Data Feed")
    else:
        logger.warning("⚠️ Failed to connect to Market Data Feed")

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "backend"}

@app.get("/health/market")
def market_health():
    return {
        "connected": market_data.is_connected, 
        "user": market_data.user_id if market_data.is_connected else None
    }

@app.post("/api/alert/create", response_model=AlertResponse)
async def create_alert(query: AlertQuery, db: Session = Depends(get_db)):
    """
    Endpoint to process natural language alert requests.
    This connects to the AI Agent (Clarification Loop).
    """
    # Instantiate the Chutes AI interpreter
    ai = AIAlertInterpreter()
    
    result = await ai.interpret(query.query)
    
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
            
            try:
                # Parse date if provided, else Default to Now
                date_str = data.get("date")
                if date_str:
                    try:
                        p_date = parser.parse(date_str)
                    except:
                        p_date = datetime.utcnow()
                else:
                    p_date = datetime.utcnow()

                new_entry = Portfolio(
                    user_id=int(query.user_id),
                    symbol=data.get("symbol"),
                    quantity=int(data.get("quantity", 0)),
                    avg_price=float(data.get("price", 0.0)),
                    purchase_date=p_date
                )
                db.add(new_entry)
                db.commit()
                
                # Format date for display
                date_disp = p_date.strftime("%d %b %Y")
                return {
                    "success": True, 
                    "status": "PORTFOLIO_ADDED",
                    "message": f"💼 Added {new_entry.quantity} {new_entry.symbol} @ {new_entry.avg_price} (Date: {date_disp})!"
                }
            except Exception as e:
                return {"success": False, "status": "ERROR", "message": f"Portfolio DB Error: {str(e)}"}

                return {
                    "success": True, 
                    "status": "PORTFOLIO_ADDED",
                    "message": f"💼 Added {new_entry.quantity} {new_entry.symbol} @ {new_entry.avg_price} (Date: {date_disp})!"
                }
            except Exception as e:
                return {"success": False, "status": "ERROR", "message": f"Portfolio DB Error: {str(e)}"}

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
                "message": "Fetching your portfolio..."
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
    holdings = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
    return {
        "user_id": user_id,
        "holdings": [
            {
                "symbol": h.symbol,
                "quantity": h.quantity,
                "avg_price": h.avg_price,
                "date": h.purchase_date
            } for h in holdings
        ]
    }
