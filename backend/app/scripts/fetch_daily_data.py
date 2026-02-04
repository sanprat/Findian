"""
Fetch daily stock data from yfinance and store in database.
"""

import yfinance as yf
import pandas as pd
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import urllib.parse
from datetime import datetime, timedelta
import time

sys.path.append(os.path.dirname(__file__) + "/../..")

BATCH_SIZE = 50


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


def create_tables(db):
    """Create stock_daily table if not exists."""
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
    db.commit()


def get_active_symbols(db, limit=1000):
    """Get active stock symbols from database."""
    result = db.execute(
        text("SELECT symbol FROM stocks_nse WHERE is_active = TRUE LIMIT :limit"),
        {"limit": limit},
    )
    return [row[0] for row in result.fetchall()]


def fetch_and_store(symbols, db, days=5):
    """Fetch data for a batch of symbols and store in DB."""
    print(f"📥 Fetching data for {len(symbols)} symbols...")

    # Prepare yfinance tickers
    tickers = [f"{sym}.NS" for sym in symbols]
    tickers_str = " ".join(tickers)

    try:
        # Batch download
        data = yf.download(
            tickers_str,
            period=f"{days}d",
            interval="1d",
            threads=True,
            group_by="ticker",
        )

        inserted = 0
        errors = 0

        for symbol in symbols:
            try:
                # Get data for this symbol
                try:
                    sym_data = data[f"{symbol}.NS"]
                except KeyError:
                    sym_data = None

                if sym_data is None or sym_data.empty:
                    # Try with .BO
                    try:
                        sym_data = data[f"{symbol}.BO"]
                    except KeyError:
                        errors += 1
                        continue

                if sym_data is None or sym_data.empty:
                    errors += 1
                    continue

                # Get latest data
                for idx, row in sym_data.iterrows():
                    date = idx.date() if hasattr(idx, "date") else idx
                    if isinstance(date, str):
                        date = datetime.strptime(date.split()[0], "%Y-%m-%d").date()

                    # Calculate LTP and change
                    close = float(row["Close"]) if pd.notna(row["Close"]) else 0
                    prev_close = float(row["Open"]) if pd.notna(row["Open"]) else close

                    ltp = close
                    change_pct = 0
                    if prev_close > 0:
                        change_pct = ((ltp - prev_close) / prev_close) * 100

                    open_price = float(row["Open"]) if pd.notna(row["Open"]) else 0
                    high = float(row["High"]) if pd.notna(row["High"]) else 0
                    low = float(row["Low"]) if pd.notna(row["Low"]) else 0
                    volume = int(row["Volume"]) if pd.notna(row["Volume"]) else 0

                    # Upsert
                    db.execute(
                        text("""
                        INSERT INTO stock_daily (symbol, date, open, high, low, close, volume, ltp, change_pct)
                        VALUES (:symbol, :date, :open, :high, :low, :close, :volume, :ltp, :change_pct)
                        ON DUPLICATE KEY UPDATE
                            open = VALUES(open),
                            high = VALUES(high),
                            low = VALUES(low),
                            close = VALUES(close),
                            volume = VALUES(volume),
                            ltp = VALUES(ltp),
                            change_pct = VALUES(change_pct)
                    """),
                        {
                            "symbol": symbol,
                            "date": date,
                            "open": open_price,
                            "high": high,
                            "low": low,
                            "close": close,
                            "volume": volume,
                            "ltp": ltp,
                            "change_pct": round(change_pct, 2),
                        },
                    )
                    inserted += 1

                print(f"  ✅ {symbol}: {len(sym_data)} days")

            except Exception as e:
                print(f"  ❌ {symbol}: {e}")
                errors += 1

        db.commit()
        print(f"✅ Inserted {inserted} records, {errors} errors")
        return inserted, errors

    except Exception as e:
        print(f"❌ Batch fetch error: {e}")
        return 0, len(symbols)


def main():
    print("=" * 50)
    print("📊 Fetch Daily Stock Data from yfinance")
    print("=" * 50)

    db = get_db_session()

    try:
        # Create tables
        create_tables(db)

        # Get symbols
        symbols = get_active_symbols(db)
        print(f"📋 Active symbols: {len(symbols)}")

        if not symbols:
            print("⚠️ No symbols found. Run fetch_nse_stocks.py first!")
            return

        # Process in batches
        total_inserted = 0
        total_errors = 0

        for i in range(0, len(symbols), BATCH_SIZE):
            batch = symbols[i : i + BATCH_SIZE]
            print(
                f"\n📦 Batch {i // BATCH_SIZE + 1}/{(len(symbols) - 1) // BATCH_SIZE + 1}"
            )
            inserted, errors = fetch_and_store(batch, db)
            total_inserted += inserted
            total_errors += errors

            # Small delay to avoid rate limiting
            time.sleep(1)

        print(f"\n{'=' * 50}")
        print(f"✅ Total: {total_inserted} records, {total_errors} errors")
        print(f"{'=' * 50}")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
