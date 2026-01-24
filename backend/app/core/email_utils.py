"""
Email Utilities using Resend API
Resend uses HTTP API instead of SMTP, which works on cloud platforms like Railway.
"""
import os
import logging
import threading
import requests

# Load Environment Variables
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")  # Use Resend's test sender for testing
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

logger = logging.getLogger(__name__)

# Log configuration at startup (for debugging)
print(f"📧 Email Config: Resend API={'SET' if RESEND_API_KEY else 'NOT SET'}, Admin={ADMIN_EMAIL}", flush=True)


def send_email_sync(subject: str, body: str, to_email: str = None):
    """
    Send email using Resend API (HTTP-based, works on cloud platforms).
    """
    import sys
    
    recipient = to_email or ADMIN_EMAIL
    
    print(f"[EMAIL DEBUG] send_email_sync called: to={recipient}, subject={subject[:50]}", flush=True)
    
    if not RESEND_API_KEY:
        error_msg = "❌ EMAIL FAILURE: RESEND_API_KEY not set"
        print(error_msg, file=sys.stderr, flush=True)
        logger.error(error_msg)
        return False
        
    if not recipient:
        error_msg = "❌ EMAIL FAILURE: No Recipient Email (ADMIN_EMAIL not set?)"
        print(error_msg, file=sys.stderr, flush=True)
        logger.error(error_msg)
        return False

    try:
        print(f"[EMAIL DEBUG] Sending via Resend API...", flush=True)
        
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": SENDER_EMAIL,
                "to": [recipient],
                "subject": subject,
                "text": body
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            success_msg = f"✅ Email sent successfully to {recipient}: {subject} (ID: {result.get('id', 'N/A')})"
            print(success_msg, flush=True)
            logger.info(success_msg)
            return True
        else:
            error_msg = f"❌ Resend API Error: {response.status_code} - {response.text}"
            print(error_msg, file=sys.stderr, flush=True)
            logger.error(error_msg)
            return False

    except Exception as e:
        error_msg = f"❌ Failed to send email: {type(e).__name__}: {e}"
        print(error_msg, file=sys.stderr, flush=True)
        logger.error(error_msg)
        import traceback
        traceback.print_exc()
        return False


def send_email_background(background_tasks, subject: str, body: str, to_email: str = None):
    """
    Queue email sending task to FastAPI BackgroundTasks.
    """
    recipient = to_email or ADMIN_EMAIL
    
    if not background_tasks:
        # Fallback for sync contexts or testing
        thread = threading.Thread(target=send_email_sync, args=(subject, body, recipient))
        thread.start()
    else:
        background_tasks.add_task(send_email_sync, subject, body, recipient)

