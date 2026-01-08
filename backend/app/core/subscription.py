
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import User

def get_user_tier(user_id: str, db: Session) -> str:
    """Returns the user's subscription tier."""
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        return "FREE"
    
    # Expiry check removed for MVP
    # if user.subscription_expires_at ...
        
    return user.subscription_tier or "FREE"

def upgrade_user(user_id: str, tier: str, db: Session) -> bool:
    """Upgrades a user to a specific tier."""
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        return False
        
    user.subscription_tier = tier
    # Set proper expiry (e.g. 30 days from now)
    # user.subscription_expires_at = ...
    db.commit()
    return True
