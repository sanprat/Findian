from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

import urllib.parse

# Construct DATABASE_URL safely if credentials are provided
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")
db_host = os.getenv("DB_HOST", "db")

if db_user and db_password and db_name:
    encoded_password = urllib.parse.quote_plus(db_password)
    DATABASE_URL = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}:3306/{db_name}"
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/pystock")

import time
from sqlalchemy.exc import OperationalError

def get_engine(url, retries=10, delay=5):
    """Retrieve database engine with retry logic."""
    for i in range(retries):
        try:
            engine = create_engine(url)
            # Try to connect
            with engine.connect() as conn:
                print(f"✅ Database connected successfully attempt {i+1}")
                return engine
        except OperationalError:
            print(f"⚠️ Database not ready (Attempt {i+1}/{retries}). Retrying in {delay}s...")
            time.sleep(delay)
    raise Exception("Could not connect to database after multiple retries")

# Use the retry logic
if "mysql" in DATABASE_URL:
    engine = get_engine(DATABASE_URL)
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
