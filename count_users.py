#!/usr/bin/env python3
"""
Quick script to count users in the Railway database
"""
import sys
import os

# Try to read from .env for Railway URL or construct from individual variables
try:
    with open('.env', 'r') as f:
        env_vars = dict(line.strip().split('=', 1) for line in f if '=' in line and not line.startswith('#'))
except:
    env_vars = {}

# Set the DB connection string
DATABASE_URL = os.getenv('DATABASE_URL', '')

if not DATABASE_URL:
    # Try constructing from individual vars
    db_user = env_vars.get('DB_USER')
    db_password = env_vars.get('DB_PASSWORD')
    db_name = env_vars.get('DB_NAME')
    
    # Try Railway connection
    print("Enter your Railway MySQL DATABASE_URL:")
    print("(Format: mysql://user:pass@host.railway.app:port/railway)")
    DATABASE_URL = input().strip()

if not DATABASE_URL:
    print("❌ No database URL provided")
    sys.exit(1)

# Ensure mysql+pymysql driver
if DATABASE_URL.startswith('mysql://'):
    DATABASE_URL = DATABASE_URL.replace('mysql://', 'mysql+pymysql://')

from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker

try:
    engine = create_engine(DATABASE_URL, connect_args={'ssl': {'ssl_mode': 'REQUIRED'}} if 'railway' in DATABASE_URL else {})
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Query users
    result = session.execute("SELECT id, telegram_id, username, first_name, subscription_tier, created_at FROM users")
    users = result.fetchall()
    
    print(f"\n{'='*80}")
    print(f"👥 TOTAL USERS: {len(users)}")
    print(f"{'='*80}\n")
    
    if users:
        print(f"{'ID':<5} {'Telegram ID':<15} {'Username':<20} {'Name':<20} {'Tier':<10} {'Created'}")
        print(f"{'-'*95}")
        
        for user in users:
            user_id, tg_id, username, first_name, tier, created = user
            username_str = (username or 'N/A')[:19]
            first_name_str = (first_name or 'N/A')[:19]
            created_str = str(created)[:10] if created else 'N/A'
            print(f"{user_id:<5} {tg_id:<15} {username_str:<20} {first_name_str:<20} {tier:<10} {created_str}")
    
    # Count by tier
    tier_result = session.execute("SELECT subscription_tier, COUNT(*) as count FROM users GROUP BY subscription_tier")
    tier_counts = tier_result.fetchall()
    
    if tier_counts:
        print(f"\n{'='*40}")
        print("📊 BY SUBSCRIPTION TIER:")
        print(f"{'='*40}")
        for tier, count in tier_counts:
            print(f"  {tier}: {count}")
    
    session.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
