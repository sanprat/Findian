import os
import sys
import requests
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
import io
import urllib.parse

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from app.db.models import Stock
from app.db.base import Base

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Official NSE Equity List URL (or a reliable mirror)
NSE_EQUITY_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"

def get_db_session():
    # Load DB Config from Environment
    user = os.getenv("DB_USER", "user")
    password = os.getenv("DB_PASSWORD", "password")
    host = os.getenv("DB_HOST", "localhost")
    db_name = os.getenv("DB_NAME", "pystock")
    
    # Construct URL (MySQL)
    encoded_password = urllib.parse.quote_plus(password)
    database_url = f"mysql+pymysql://{user}:{encoded_password}@{host}:3306/{db_name}"
    
    # For local script execution, allow override
    if len(sys.argv) > 1 and "sqlite" in sys.argv[1]:
         database_url = "sqlite:///./pystock.db"

    logger.info(f"Connecting to DB: {user}@{host}/{db_name}")
    engine = create_engine(database_url)
    
    # Ensure tables exist
    logger.info("🛠 Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def populate_stocks():
    db = get_db_session()
    
    try:
        logger.info("📥 Fetching Stock List...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        df = None
        try:
             # Try direct simple CSV first
             response = requests.get(NSE_EQUITY_URL, headers=headers, timeout=10)
             response.raise_for_status()
             df = pd.read_csv(io.StringIO(response.text))
        except Exception as e:
             logger.warning(f"Download failed ({e}). Using fallback data...")
             # Fallback: Major Nifty 50 Stocks
             data = {
                 "Symbol": ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "BAJFINANCE", "ELECON", "TATAMOTORS", "ZOMATO", "KPITTECH", "TRIDENT", "SUZLON"],
                 "Company Name": ["Reliance Industries Ltd", "Tata Consultancy Services", "HDFC Bank", "Infosys Limited", "ICICI Bank", "Hindustan Unilever", "ITC Limited", "State Bank of India", "Bharti Airtel", "Bajaj Finance", "Elecon Engineering", "Tata Motors Limited", "Zomato Limited", "KPIT Technologies", "Trident Ltd", "Suzlon Energy"]
             }
             df = pd.DataFrame(data)

        # Normalize Columns
        # Expecting 'Symbol', 'Company Name' ('NAME OF COMPANY' in some csvs)
        # Check available columns
        logger.info(f"Columns found: {df.columns}")
        
        if 'Symbol' not in df.columns:
            # Map standard NSE CSV headers if different
            # Often: 'SYMBOL', 'NAME OF COMPANY'
            df.rename(columns={'SYMBOL': 'Symbol', 'NAME OF COMPANY': 'Company Name'}, inplace=True)
            
        count = 0
        updated = 0
        
        for index, row in df.iterrows():
            symbol = str(row['Symbol']).upper().strip()
            name = str(row.get('Company Name', '')).strip()
            
            if not symbol or symbol == 'NAN':
                continue
                
            # Check if exists
            existing = db.query(Stock).filter(Stock.symbol == symbol).first()
            
            if existing:
                if existing.name != name:
                    existing.name = name
                    updated += 1
            else:
                new_stock = Stock(
                    symbol=symbol,
                    name=name,
                    exchange="NSE",
                    is_active=True
                )
                db.add(new_stock)
                count += 1
                
            if index % 100 == 0:
                print(f"Processed {index} stocks...", end="\r")
        
        db.commit()
        logger.info(f"\n✅ Finished! Added: {count}, Updated: {updated}")
        
    except Exception as e:
        logger.error(f"Error populating stocks: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    populate_stocks()
