import logging
import re
from sqlalchemy import text
from app.db.base import engine

logger = logging.getLogger("uvicorn")

# SECURITY: Whitelist of allowed table and column names to prevent SQL injection
ALLOWED_TABLES = {"users", "trade_history", "alerts", "portfolio", "saved_scans"}
ALLOWED_COLUMNS = {
    "subscription_tier", "last_name", "first_name", "username",
    "trade_type", "realized_pnl", "symbol", "quantity", "price"
}
# Pattern for valid SQL identifiers (alphanumeric and underscore only)
IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

def _validate_identifier(name: str, allowed_set: set) -> bool:
    """
    SECURITY: Validates that an identifier is safe to use in SQL.
    Returns True only if the name matches the pattern AND is in the whitelist.
    """
    if not name or len(name) > 64:
        return False
    if not IDENTIFIER_PATTERN.match(name):
        return False
    return name.lower() in {x.lower() for x in allowed_set}

def check_and_fix_schema():
    """
    Checks for missing columns in critical tables and adds them if missing.
    This acts as a poor-man's migration for Railway where we can't easily run Alembic.
    
    SECURITY: Uses whitelist validation for all table/column names to prevent SQL injection.
    """
    logger.info("🔍 Checking Database Schema...")
    
    # Define conversions: Table -> {Column: Type}
    # SECURITY: Column types are hardcoded, not user-supplied
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
            # SECURITY: Validate table name against whitelist
            if not _validate_identifier(table, ALLOWED_TABLES):
                logger.error(f"❌ SECURITY: Invalid table name rejected: {table}")
                continue
                
            for col, col_type in cols.items():
                # SECURITY: Validate column name against whitelist
                if not _validate_identifier(col, ALLOWED_COLUMNS):
                    logger.error(f"❌ SECURITY: Invalid column name rejected: {col}")
                    continue
                    
                try:
                    # Check if column exists using parameterized query for the LIKE value
                    # Note: Table/column names cannot be parameterized in SQL, hence whitelist validation above
                    check_sql = text(f"SHOW COLUMNS FROM `{table}` LIKE :col_name")
                    result = conn.execute(check_sql, {"col_name": col}).fetchone()
                    
                    if not result:
                        logger.warning(f"⚠️ Missing column '{col}' in '{table}'. Adding it...")
                        # SECURITY: col_type is from our hardcoded dict, not user input
                        alter_sql = text(f"ALTER TABLE `{table}` ADD COLUMN `{col}` {col_type}")
                        conn.execute(alter_sql)
                        conn.commit()
                        logger.info(f"✅ Added column '{col}' to '{table}'")
                except Exception as e:
                    # SECURITY: Don't expose internal error details in logs that might be to users
                    logger.error(f"❌ Schema check failed for {table}.{col}: {type(e).__name__}")
                    
    logger.info("✅ Schema Check Complete")
