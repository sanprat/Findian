import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
import threading

# Load Environment Variables
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_USERNAME)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", SENDER_EMAIL)

logger = logging.getLogger(__name__)

# Log configuration at startup (for debugging)
logger.info(f"📧 Email Config Loaded: SMTP={SMTP_SERVER}:{SMTP_PORT}, Username={'SET' if SMTP_USERNAME else 'NOT SET'}, Password={'SET' if SMTP_PASSWORD else 'NOT SET'}, Admin={ADMIN_EMAIL}")

def send_email_sync(subject: str, body: str, to_email: str = ADMIN_EMAIL):
    """
    Synchronous function to send email via SMTP.
    Use this within a background thread/task.
    Uses SMTP_SSL (port 465) which works better on cloud platforms.
    """
    import sys
    
    print(f"[EMAIL DEBUG] send_email_sync called: to={to_email}, subject={subject[:50]}", flush=True)
    
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        error_msg = f"❌ EMAIL FAILURE: Missing Credentials. User:{SMTP_USERNAME}, Pass:{'SET' if SMTP_PASSWORD else 'MISSING'}"
        print(error_msg, file=sys.stderr, flush=True)
        logger.error(error_msg)
        return
        
    if not to_email:
        error_msg = "❌ EMAIL FAILURE: No Recipient Email (ADMIN_EMAIL not set?)"
        print(error_msg, file=sys.stderr, flush=True)
        logger.error(error_msg)
        return

    try:
        # Create Message
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        # Try SMTP_SSL on port 465 first (works better on cloud platforms)
        print(f"[EMAIL DEBUG] Connecting via SSL to {SMTP_SERVER}:465...", flush=True)
        
        try:
            import ssl
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(SMTP_SERVER, 465, timeout=30, context=context)
            print(f"[EMAIL DEBUG] SSL Connected! Logging in as {SMTP_USERNAME}...", flush=True)
        except Exception as ssl_err:
            # Fallback to STARTTLS on port 587
            print(f"[EMAIL DEBUG] SSL failed ({ssl_err}), trying STARTTLS on 587...", flush=True)
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
            server.starttls()
            print(f"[EMAIL DEBUG] STARTTLS Connected! Logging in...", flush=True)
        
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        print(f"[EMAIL DEBUG] Login successful! Sending email...", flush=True)
        
        # Send Email
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, to_email, text)
        server.quit()
        
        success_msg = f"✅ Email sent successfully to {to_email}: {subject}"
        print(success_msg, flush=True)
        logger.info(success_msg)

    except Exception as e:
        error_msg = f"❌ Failed to send email: {type(e).__name__}: {e}"
        print(error_msg, file=sys.stderr, flush=True)
        logger.error(error_msg)
        import traceback
        traceback.print_exc()

def send_email_background(background_tasks, subject: str, body: str, to_email: str = ADMIN_EMAIL):
    """
    Queue email sending task to FastAPI BackgroundTasks.
    """
    if not background_tasks:
        # Fallback for sync contexts or testing
        thread = threading.Thread(target=send_email_sync, args=(subject, body, to_email))
        thread.start()
    else:
        background_tasks.add_task(send_email_sync, subject, body, to_email)
