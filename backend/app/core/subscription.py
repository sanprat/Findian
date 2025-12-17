
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import User

def get_user_tier(user_id: str, db: Session) -> str:
    """Returns the user's subscription tier."""
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        return "FREE"
    
    # Check expiry
    if user.subscription_expires_at and user.subscription_expires_at < datetime.utcnow():
        # Expired? Downgrade logic could go here or just return FREE
        # For now, let's just return what's in DB but treat as FREE if expired
        # (Assuming we have a cron to downgrade, or we check on read)
        return "FREE"
        
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
