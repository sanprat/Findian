import requests
import os

# Configuration
BACKEND_URL = "http://localhost:8000"
API_KEY = "dummy_secret" # Assuming dev/test key where needed or relying on no-auth for local if configured so. 
# Wait, backend requires X-API-Key. I need to find the key or temporarily mock it or Assume running locally implies I can access env.
# In the `main.py` I saw `API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")` and defaults empty?
# If empty, `APIKeyAuthMiddleware` fails: "SECURITY: API_SECRET_KEY not configured - rejecting request"
# Unless it's empty string... 
# "if not API_SECRET_KEY: return 500"
# So I must check if I can send a valid key.
# I'll check if there is an .env or just try to use a known key if I can find one. 
# Or I can try to run this test assuming the server is running with some key.

# Actually, I can't easily start the server in this environment to serve requests unless I use `run_command` with background.
# But I can use `fastapi.testclient`! That's much better for unit testing without a running server.

from fastapi.testclient import TestClient
from app.main import app
import os

from fastapi.testclient import TestClient
from app.main import app, get_db
import os
from unittest.mock import MagicMock

# Validation override (if needed, but we want to test logic)
# We override the DB dependency

def override_get_db():
    try:
        db = MagicMock()
        # Mock add/commit to do nothing
        db.add.return_value = None
        db.commit.return_value = None
        yield db
    finally:
        pass

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_feedback_submission():
    headers = {"X-API-Key": "test_secret"}
    
    # Test 1: Valid Feedback
    payload = {
        "user_id": "123456789",
        "category": "FEEDBACK",
        "message": "This is a great bot! Love the features."
    }
    response = client.post("/api/support/submit", json=payload, headers=headers)
    print(f"Test 1 (Valid): {response.status_code} - {response.json()}")
    assert response.status_code == 200
    assert response.json()["success"] == True

    # Test 2: Valid Issue
    payload = {
        "user_id": "123456789",
        "category": "ISSUE",
        "message": "I found a bug in the screener."
    }
    response = client.post("/api/support/submit", json=payload, headers=headers)
    print(f"Test 2 (Valid Issue): {response.status_code} - {response.json()}")
    assert response.status_code == 200

    # Test 3: Invalid Category
    payload = {
        "user_id": "123456789",
        "category": "INVALID",
        "message": "Hello"
    }
    response = client.post("/api/support/submit", json=payload, headers=headers)
    print(f"Test 3 (Invalid Category): {response.status_code} - {response.json()}")
    assert response.status_code == 400

    # Test 4: Message Too Short
    payload = {
        "user_id": "123456789",
        "category": "FEEDBACK",
        "message": "Hi"
    }
    response = client.post("/api/support/submit", json=payload, headers=headers)
    print(f"Test 4 (Short Msg): {response.status_code} - {response.json()}")
    assert response.status_code == 400

if __name__ == "__main__":
    try:
        test_feedback_submission()
        print("\n✅ All Feedback Tests Passed!")
    except Exception as e:
        print(f"\n❌ Tests Failed: {e}")
