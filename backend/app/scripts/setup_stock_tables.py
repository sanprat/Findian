"""
Create SQL tables for stock data storage.
"""

import os
import sys
import urllib.parse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(__file__) + "/../..")


def get_db_session():
    user = os.getenv("DB_USER", "sanprat")
    password = os.getenv("DB_PASSWORD", "LetsLearn@2025")
    host = os.getenv("DB_HOST", "localhost")
    db_name = os.getenv("DB_NAME", "pystock")

    encoded_password = urllib.parse.quote_plus(password)
    database_url = f"mysql+pymysql://{user}:{encoded_password}@{host}:3306/{db_name}"

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def create_tables():
    db = get_db_session()

    try:
        # Stocks NSE list
        db.execute(
            text("""
            CREATE TABLE IF NOT EXISTS stocks_nse (
                id INT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(255),
                exchange VARCHAR(20) DEFAULT 'NSE',
                is_active BOOLEAN DEFAULT TRUE,
                last_updated DATETIME,
                INDEX idx_symbol (symbol),
                INDEX idx_active (is_active)
            )
        """)
        )

        # Daily price data
        db.execute(
            text("""
            CREATE TABLE IF NOT EXISTS stock_daily (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(50) NOT NULL,
                date DATE NOT NULL,
                open DECIMAL(15,2),
                high DECIMAL(15,2),
                low DECIMAL(15,2),
                close DECIMAL(15,2),
                volume BIGINT,
                ltp DECIMAL(15,2),
                change_pct DECIMAL(10,2),
                created_at DATETIME DEFAULT NOW(),
                UNIQUE KEY uk_symbol_date (symbol, date),
                INDEX idx_symbol (symbol),
                INDEX idx_date (date),
                INDEX idx_ltp (ltp)
            )
        """)
        )

        # Fundamentals
        db.execute(
            text("""
            CREATE TABLE IF NOT EXISTS stock_fundamentals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(50) UNIQUE NOT NULL,
                pe_ratio DECIMAL(10,2),
                pb_ratio DECIMAL(10,2),
                roe DECIMAL(10,2),
                debt_to_equity DECIMAL(10,2),
                dividend_yield DECIMAL(10,2),
                market_cap BIGINT,
                eps DECIMAL(10,2),
                book_value DECIMAL(10,2),
                sector VARCHAR(100),
                industry VARCHAR(100),
                high_52w DECIMAL(15,2),
                low_52w DECIMAL(15,2),
                avg_volume_20 BIGINT,
                rsi_14 DECIMAL(10,2),
                last_updated DATETIME DEFAULT NOW(),
                INDEX idx_symbol (symbol),
                INDEX idx_pe (pe_ratio),
                INDEX idx_mcap (market_cap)
            )
        """)
        )

        db.commit()
        print("✅ All tables created successfully!")

        # Show tables
        result = db.execute(text("SHOW TABLES")).fetchall()
        print("\n📋 Tables in database:")
        for row in result:
            print(f"  - {row[0]}")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_tables()
