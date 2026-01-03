from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import os
import time
import socket
import urllib.parse
import sys

# Construct DATABASE_URL safely
# Priority: Use DATABASE_URL if provided (Railway), else construct from individual vars (Docker)
DATABASE_URL = os.getenv("DATABASE_URL", "")

print(f"🔧 Database Configuration Check...")
print(f"   - DATABASE_URL present: {bool(DATABASE_URL)}")
print(f"   - DB_HOST env: {os.getenv('DB_HOST', 'NOT SET')}")

if DATABASE_URL:
    # Don't log the full URL as it contains credentials
    print(f"✅ Using provided DATABASE_URL from environment")
else:
    # Construct from individual credentials (Docker Compose)
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
    db_host = os.getenv("DB_HOST")  # No default - fail explicitly if not set

    if db_user and db_password and db_name and db_host:
        # Mask sensitive info - only show non-sensitive parts
        host_preview = db_host[:10] + "..." if len(db_host) > 10 else db_host
        print(f"🔧 Constructing DATABASE_URL (Host={host_preview}, DB={db_name})")
        encoded_password = urllib.parse.quote_plus(db_password)
        DATABASE_URL = (
            f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}:3306/{db_name}"
        )
    else:
        print("❌ FATAL: Database configuration missing!")
        print(
            "   Required: Either DATABASE_URL or all of (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)"
        )
        print(f"   DB_HOST: {'✅' if db_host else '❌ MISSING'}")
        print(f"   DB_USER: {'✅' if db_user else '❌ MISSING'}")
        print(f"   DB_PASSWORD: {'✅' if db_password else '❌ MISSING'}")
        print(f"   DB_NAME: {'✅' if db_name else '❌ MISSING'}")
        # Exit early with clear error instead of cryptic crash
        sys.exit(1)


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
    last_error = None

    for i in range(retries):
        try:
            connect_args = {}

            # Railway MySQL requires SSL connection
            if url.startswith("mysql"):
                connect_args = {"ssl": {"ssl_mode": "REQUIRED"}}

                # Pre-check TCP connectivity (only on first attempt)
                if i == 0:
                    try:
                        host_part = url.split("@")[1].split("/")[0]
                        if ":" in host_part:
                            host = host_part.split(":")[0]
                            port = int(host_part.split(":")[1])
                        else:
                            host = host_part
                            port = 3306

                        print(f"🔍 Checking database connectivity to {host}:{port}...")
                        wait_for_db(host, port, timeout=30)
                    except Exception as parse_error:
                        print(f"⚠️ TCP pre-check failed: {parse_error}")
                        # Continue anyway - let SQLAlchemy try

            engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)

            # Try to connect
            with engine.connect() as conn:
                print(f"✅ Database connected successfully (attempt {i + 1})")
                return engine

        except OperationalError as e:
            last_error = e
            print(f"⚠️ Database not ready (Attempt {i + 1}/{retries})")
            print(f"   Error: {str(e)[:100]}...")
            if i < retries - 1:  # Don't sleep on last attempt
                print(f"   Retrying in {delay}s...")
                time.sleep(delay)

        except Exception as e:
            last_error = e
            print(f"❌ Unexpected DB Error (Attempt {i + 1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)

    raise Exception(
        f"Could not connect to database after {retries} retries. Last error: {last_error}"
    )


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
