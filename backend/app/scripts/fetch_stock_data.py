"""
Fetch stock data (price + fundamentals) from yfinance and store in SQL database.
This script is for populating all NSE stocks' data into the database.
Run this periodically to keep data fresh.
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
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

BATCH_SIZE = 50
MAX_WORKERS = 5  # Parallel downloads

sys.path.append(os.path.dirname(__file__) + "/../..")

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

    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def get_active_symbols(db, limit=2000):
    """Get active stock symbols from database."""
    result = db.execute(
        text("SELECT symbol FROM stocks_nse WHERE is_active = TRUE LIMIT :limit"),
        {"limit": limit}
    )
    return [row[0] for row in result.fetchall()]

def fetch_price_data(symbols, db, days=5):
    """Fetch daily price data for symbols and store in DB."""
    print(f"📥 Fetching price data for {len(symbols)} symbols...")

    if not symbols:
        print("⚠️ No symbols to fetch")
        return 0, 0

    tickers = [f"{sym}.NS" for sym in symbols]
    tickers_str = " ".join(tickers)

    try:
        # Batch download
        data = yf.download(tickers_str, period=f"{days}d", interval="1d", threads=True, group_by='ticker', progress=True)

        inserted = 0
        errors = 0

        for symbol in symbols:
            try:
                # Get data for this symbol
                try:
                    sym_data = data[symbol.replace('.NS', '.NS')] if isinstance(data.columns, pd.MultiIndex) else data
                except:
                    sym_data = None

                if sym_data is None or sym_data.empty:
                    errors += 1
                    continue

                if sym_data is None or sym_data.empty:
                    errors += 1
                    continue

                # Get the data for this symbol
                if isinstance(data.columns, pd.MultiIndex):
                    try:
                        sym_data = data[symbol]
                    except KeyError:
                        errors += 1
                        continue
                else:
                    sym_data = data

                if sym_data.empty:
                    errors += 1
                    continue

                # Process latest data point
                for idx, row in sym_data.iterrows():
                    date = idx.date() if hasattr(idx, 'date') else idx
                    if isinstance(date, str):
                        date = datetime.strptime(date.split()[0], '%Y-%m-%d').date()

                    close = float(row['Close']) if pd.notna(row['Close']) else 0
                    prev_close = float(row['Open']) if pd.notna(row['Open']) else close

                    ltp = close
                    change_pct = 0
                    if prev_close > 0:
                        change_pct = ((ltp - prev_close) / prev_close) * 100

                    open_price = float(row['Open']) if pd.notna(row['Open']) else 0
                    high = float(row['High']) if pd.notna(row['High']) else 0
                    low = float(row['Low']) if pd.notna(row['Low']) else 0
                    volume = int(row['Volume']) if pd.notna(row['Volume']) else 0

                    db.execute(text("""
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
                    """), {
                        "symbol": symbol,
                        "date": date,
                        "open": open_price,
                        "high": high,
                        "low": low,
                        "close": close,
                        "volume": volume,
                        "ltp": ltp,
                        "change_pct": round(change_pct, 2)
                    })
                    inserted += 1

                print(f"  ✅ {symbol}: {len(sym_data)} days")

            except Exception as e:
                print(f"  ❌ {symbol}: {e}")
                errors += 1

        db.commit()
        print(f"✅ Inserted {inserted} price records, {errors} errors")
        return inserted, errors

    except Exception as e:
        print(f"❌ Batch fetch error: {e}")
        return 0, len(symbols)

def fetch_fundamentals(symbols, db):
    """Fetch fundamentals for symbols and store in DB."""
    print(f"\n📊 Fetching fundamentals for {len(symbols)} symbols...")

    inserted = 0
    errors = 0

    for symbol in symbols:
        try:
            ticker = yf.Ticker(f"{symbol}.NS}")
            info = ticker.info

            if not info:
                errors += 1
                continue

            # Extract fundamentals
            pe_ratio = info.get("trailingPE")
            pb_ratio = info.get("priceToBook")
            roe = info.get("returnOnEquity")
            if roe:
                roe = round(roe * 100, 2)

            debt_to_equity = info.get("debtToEquity")
            dividend_yield = info.get("dividendYield")
            if dividend_yield:
                dividend_yield = round(dividend_yield * 100, 2)

            market_cap = info.get("marketCap")
            eps = info.get("trailingEps")
            book_value = info.get("bookValue")
            sector = info.get("sector")
            industry = info.get("industry")
            high_52w = info.get("fiftyTwoWeekHigh")
            low_52w = info.get("fiftyTwoWeekLow")

            # Calculate RSI (14-day)
            hist = ticker.history(period="3mo")
            rsi_14 = None
            if len(hist) >= 14:
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi_14 = round((100 - (100 / (1 + rs))).iloc[-1], 2)
            elif len(hist) >= 5:
                rsi_14 = 50  # Default if not enough data

            # Calculate 20-day average volume
            avg_volume_20 = None
            if len(hist) >= 20:
                avg_volume_20 = int(hist['Volume'].tail(20).mean())

            # Upsert fundamentals
            db.execute(text("""
                INSERT INTO stock_fundamentals (
                    symbol, pe_ratio, pb_ratio, roe, debt_to_equity, dividend_yield,
                    market_cap, eps, book_value, sector, industry,
                    high_52w, low_52w, avg_volume_20, rsi_14, last_updated
                ) VALUES (
                    :symbol, :pe_ratio, :pb_ratio, :roe, :debt_to_equity, :dividend_yield,
                    :market_cap, :eps, :book_value, :sector, :industry,
                    :high_52w, :low_52w, :avg_volume_20, :rsi_14, NOW()
                )
                ON DUPLICATE KEY UPDATE
                    pe_ratio = :pe_ratio,
                    pb_ratio = :pb_ratio,
                    roe = :roe,
                    debt_to_equity = :debt_to_equity,
                    dividend_yield = :dividend_yield,
                    market_cap = :market_cap,
                    eps = :eps,
                    book_value = :book_value,
                    sector = :sector,
                    industry = :industry,
                    high_52w = :high_52w,
                    low_52w = :low_52w,
                    avg_volume_20 = :avg_volume_20,
                    rsi_14 = :rsi_14,
                    last_updated = NOW()
            """), {
                "symbol": symbol,
                "pe_ratio": pe_ratio,
                "pb_ratio": pb_ratio,
                "roe": roe,
                "debt_to_equity": debt_to_equity,
                "dividend_yield": dividend_yield,
                "market_cap": market_cap,
                "eps": eps,
                "book_value": book_value,
                "sector": sector,
                "industry": industry,
                "high_52w": high_52w,
                "low_52w": low_52w,
                "avg_volume_20": avg_volume_20,
                "rsi_14": rsi_14
            })

            inserted += 1
            print(f"  ✅ {symbol}: PE={pe_ratio}, ROE={roe}%, MCap={market_cap}")

            # Rate limiting for yfinance
            time.sleep(0.3)

        except Exception as e:
            print(f"  ❌ {symbol}: {e}")
            errors += 1

    db.commit()
    print(f"✅ Upserted {inserted} fundamentals, {errors} errors")
    return inserted, errors

def main():
    print("=" * 60)
    print("📊 Fetch Stock Data (Price + Fundamentals) from yfinance")
    print("=" * 60)

    db = get_db_session()

    try:
        # Get symbols
        symbols = get_active_symbols(db)
        print(f"📋 Active symbols in DB: {len(symbols)}")

        if not symbols:
            print("⚠️ No symbols found. Run setup_stock_tables.py and populate_stocks.py first!")
            return

        # Process in batches
        total_price_inserted = 0
        total_price_errors = 0
        total_fund_inserted = 0
        total_fund_errors = 0

        for i in range(0, len(symbols), BATCH_SIZE):
            batch = symbols[i:i + BATCH_SIZE]
            print(f"\n📦 Batch {i//BATCH_SIZE + 1}/{(len(symbols)-1)//BATCH_SIZE + 1}")

            # Fetch price data
            price_inserted, price_errors = fetch_price_data(batch, db)
            total_price_inserted += price_inserted
            total_price_errors += price_errors

            # Fetch fundamentals
            fund_inserted, fund_errors = fetch_fundamentals(batch, db)
            total_fund_inserted += fund_inserted
            total_fund_errors += fund_errors

            # Small delay to avoid rate limiting
            time.sleep(2)

        print(f"\n{'='*60}")
        print("📊 SUMMARY")
        print(f"  Price Data: {total_price_inserted} inserted, {total_price_errors} errors")
        print(f"  Fundamentals: {total_fund_inserted} upserted, {total_fund_errors} errors")
        print(f"{'='*60}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
