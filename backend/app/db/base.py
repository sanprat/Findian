from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

import urllib.parse

# Construct DATABASE_URL safely
# Priority: Use DATABASE_URL if provided (Railway), else construct from individual vars (Docker)
DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL:
    print(f"DEBUG: Using provided DATABASE_URL")
else:
    # Construct from individual credentials (Docker Compose)
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    db_host = os.getenv("DB_HOST", "db")
    
    if db_user and db_password and db_name:
        print(f"DEBUG: Constructing DATABASE_URL from vars. User={db_user}, Host={db_host}, Name={db_name}")
        encoded_password = urllib.parse.quote_plus(db_password)
        DATABASE_URL = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}:3306/{db_name}"
    else:
        print("❌ ERROR: No DATABASE_URL and missing DB credentials!")
        print(f"Available Env Keys: {list(os.environ.keys())}")

import time
import socket
from sqlalchemy.exc import OperationalError

def wait_for_db(host: str, port: int = 3306, timeout: int = 60):
    """Wait for database to be reachable via TCP (handles DNS delay)."""
    start_time = time.time()
    while True:
        try:
            # Try 3 second timeout for connection
            with socket.create_connection((host, port), timeout=3):
                print(f"✅ Database {host}:{port} is reachable via TCP.")
                return True
        except (socket.gaierror, socket.error) as e:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                print(f"❌ Timeout waiting for DB {host}:{port}. Last error: {e}")
                raise Exception(f"Database {host} unreachable after {timeout}s")
            
            print(f"⏳ Waiting for DB {host}:{port} to be ready... ({e})")
            time.sleep(2)

# Fix for SQLAlchemy requiring 'mysql+pymysql' instead of 'mysql' if we don't have mysqlclient installed
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://")

def get_engine(url, retries=10, delay=5):
    """Retrieve database engine with retry logic."""
    for i in range(retries):
        try:
            # Pre-check TCP connectivity (only on first attempt)
            if i == 0 and url.startswith("mysql"):
                # Extract host from URL: mysql+pymysql://user:pass@HOST:PORT/db
                try:
                    host_part = url.split("@")[1].split("/")[0]  # Gets "HOST:PORT"
                    if ":" in host_part:
                        host = host_part.split(":")[0]
                        port = int(host_part.split(":")[1])
                    else:
                        host = host_part
                        port = 3306
                    
                    print(f"🔍 Checking database connectivity to {host}:{port}...")
                    wait_for_db(host, port)
                except Exception as parse_error:
                    print(f"⚠️ Could not parse host from URL, skipping pre-check: {parse_error}")

            connect_args = {}
            
            engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
            
            # Try to connect
            with engine.connect() as conn:
                print(f"✅ Database connected successfully attempt {i+1}")
                return engine
        except OperationalError as e:
            print(f"⚠️ Database not ready (Attempt {i+1}/{retries}). Error: {e}")
            print(f"Retrying in {delay}s...")
            time.sleep(delay)
        except Exception as e:
             print(f"❌ Critical DB Connection Error: {e}")
             time.sleep(delay)
             
    raise Exception("Could not connect to database after multiple retries")

# Use the retry logic
engine = get_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
