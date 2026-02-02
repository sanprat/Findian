
import asyncio
from dotenv import load_dotenv
load_dotenv()
from app.db.base import SessionLocal
from app.db.models import User

def check_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"👥 Total Users: {len(users)}")
        for u in users:
            print(f"ID: {u.id}, TG_ID: {u.telegram_id}, Name: {u.first_name}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()
