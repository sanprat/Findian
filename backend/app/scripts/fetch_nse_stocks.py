"""
Fetch all NSE stock symbols from yfinance and store in database.
"""

import yfinance as yf
import pandas as pd
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import urllib.parse

sys.path.append(os.path.dirname(__file__) + "/../..")

from app.db.base import Base


def get_db_session():
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")

    if not all([user, password, host, db_name]):
        raise ValueError(
            "Missing database configuration. Set DB_USER, DB_PASSWORD, DB_HOST, and DB_NAME."
        )

    encoded_password = urllib.parse.quote_plus(password)
    database_url = f"mysql+pymysql://{user}:{encoded_password}@{host}:3306/{db_name}"

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def fetch_nse_stocks():
    """Fetch all available NSE stock tickers from yfinance."""
    print("📥 Fetching NSE stock list from yfinance...")

    try:
        # Use yfinance to get nifty 500 tickers
        nifty500 = yf.Indices("^NSEI")
        # This gives us Nifty 50, we need more stocks

        # Alternative: Try to get list from NSE
        # For now, use major indices and expand
        major_indices = [
            "^NSEI",  # Nifty 50
            "^NSE100",  # Nifty 100
            "^NSEMD100",  # Nifty Midcap 100
            "^NSESMALL",  # Nifty Smallcap 250
        ]

        all_tickers = set()

        for index in major_indices:
            try:
                idx = yf.Ticker(index)
                constituents = idx.constituents
                if constituents:
                    for sym in constituents:
                        if not sym.endswith(".BO"):
                            all_tickers.add(sym.replace(".NS", ""))
            except Exception as e:
                print(f"  Warning: Could not fetch {index}: {e}")

        # Also fetch from a broader list
        # Try Nifty Next 50
        try:
            nifty_next = yf.Ticker("^NXTCLOSE")
            const = nifty_next.constituents
            if const:
                for sym in const:
                    if not sym.endswith(".BO"):
                        all_tickers.add(sym.replace(".NS", ""))
        except:
            pass

        print(f"📊 Found {len(all_tickers)} unique tickers")
        return list(all_tickers)

    except Exception as e:
        print(f"❌ Error fetching stock list: {e}")
        # Fallback to empty list
        return []


def fetch_company_names(tickers):
    """Fetch company names for tickers."""
    print("📥 Fetching company names...")
    company_data = []

    for i, sym in enumerate(tickers):
        try:
            ticker = yf.Ticker(f"{sym}.NS")
            info = ticker.info
            name = info.get("longName", info.get("shortName", sym))
            company_data.append({"symbol": sym, "name": name})
            print(f"  [{i + 1}/{len(tickers)}] {sym}: {name[:30]}...")
        except Exception as e:
            company_data.append({"symbol": sym, "name": sym})
            print(f"  [{i + 1}/{len(tickers)}] {sym}: (no data)")

    return company_data


def main():
    db = get_db_session()

    try:
        # Ensure table exists
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
        db.commit()

        # Fetch tickers
        tickers = fetch_nse_stocks()

        if not tickers:
            print("⚠️ No tickers found, using fallback list...")
            # Major NSE stocks fallback
            tickers = [
                "RELIANCE",
                "TCS",
                "HDFCBANK",
                "INFY",
                "ICICIBANK",
                "HINDUNILVR",
                "ITC",
                "SBIN",
                "BHARTIARTL",
                "KOTAKBANK",
                "LTIM",
                "AXISBANK",
                "LT",
                "BAJFINANCE",
                "MARUTI",
                "ASIANPAINT",
                "HCLTECH",
                "TITAN",
                "SUNPHARMA",
                "ULTRACEMCO",
                "TATASTEEL",
                "NTPC",
                "POWERGRID",
                "WIPRO",
                "NESTLEIND",
                "ONGC",
                "M&M",
                "INDUSINDBK",
                "JSWSTEEL",
                "ADANIENT",
                "ADANIPORTS",
                "COALINDIA",
                "BPCL",
                "GRASIM",
                "HEROMOTOCO",
                "HINDALCO",
                "TECHM",
                "EICHERMOT",
                "DIVISLAB",
                "CIPLA",
                "DRREDDY",
                "SBILIFE",
                "BAJAJFINSV",
                "BRITANNIA",
                "APOLLOHOSP",
                "TATACONSUM",
                "UPL",
                "SHRIRAMFIN",
                "TATAMOTORS",
                "ZOMATO",
                "PAYTM",
                "DMART",
                "HAL",
                "LICNAM",
                "RECLTD",
                "BANDHANBNK",
                "SBI life insurance",
                "HDFC Life",
                "ICICI Pru",
                "NMDC",
                "JINDALSTEL",
                "JSWENERGY",
                "ADANIENSOL",
                "ADANIGREEN",
                "ADANITRANS",
                "SIEMENS",
                "BEL",
                "BHEL",
                "COFORGE",
                "MINDTREE",
                "LTI",
                "PERSISTENT",
                "CMP",
                "RAMCOSYS",
                "TATAELXSI",
            ]

        # Fetch company names
        company_data = fetch_company_names(tickers)

        # Store in database
        count = 0
        for data in company_data:
            symbol = data["symbol"].upper().strip()
            name = data["name"][:255] if data["name"] else symbol

            # Check if exists
            existing = db.execute(
                text("SELECT id FROM stocks_nse WHERE symbol = :symbol"),
                {"symbol": symbol},
            ).fetchone()

            if existing:
                db.execute(
                    text(
                        "UPDATE stocks_nse SET name = :name, last_updated = NOW() WHERE symbol = :symbol"
                    ),
                    {"symbol": symbol, "name": name},
                )
            else:
                db.execute(
                    text(
                        "INSERT INTO stocks_nse (symbol, name, exchange, is_active, last_updated) VALUES (:symbol, :name, 'NSE', TRUE, NOW())"
                    ),
                    {"symbol": symbol, "name": name},
                )
                count += 1

        db.commit()
        print(f"✅ Added {count} new stocks. Total stocks in DB: {len(company_data)}")

        # Show sample
        result = db.execute(
            text("SELECT symbol, name FROM stocks_nse LIMIT 10")
        ).fetchall()
        print("\n📋 Sample stocks:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
