import logging
from sqlalchemy import text
from app.db.base import engine

logger = logging.getLogger("uvicorn")

def check_and_fix_schema():
    """
    Checks for missing columns in critical tables and adds them if missing.
    This acts as a poor-man's migration for Railway where we can't easily run Alembic.
    """
    logger.info("🔍 Checking Database Schema...")
    
    # Define conversions: Table -> {Column: Type}
    required_columns = {
        "users": {
            "subscription_tier": "VARCHAR(50) DEFAULT 'FREE'",
            "last_name": "VARCHAR(255)"
        },
        "trade_history": {
            "trade_type": "VARCHAR(10)",
            "realized_pnl": "FLOAT"
        },
        # Add others if needed
    }
    
    with engine.connect() as conn:
        for table, cols in required_columns.items():
            for col, col_type in cols.items():
                try:
                    # Check if column exists
                    check_sql = text(f"SHOW COLUMNS FROM {table} LIKE '{col}'")
                    result = conn.execute(check_sql).fetchone()
                    
                    if not result:
                        logger.warning(f"⚠️ Missing column '{col}' in '{table}'. Adding it...")
                        alter_sql = text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                        conn.execute(alter_sql)
                        conn.commit()
                        logger.info(f"✅ Added column '{col}' to '{table}'")
                except Exception as e:
                    logger.error(f"❌ Schema check failed for {table}.{col}: {e}")
                    
    logger.info("✅ Schema Check Complete")
