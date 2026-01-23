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
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.error(f"❌ EMAIL FAILURE: Missing Credentials. User:{SMTP_USERNAME}")
        return
        
    if not to_email:
        logger.error("❌ EMAIL FAILURE: No Recipient Email (ADMIN_EMAIL not set?)")
        return

    try:
        # Create Message
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        # Connect to Server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Secure the connection
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        # Send Email
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, to_email, text)
        server.quit()
        
        logger.info(f"✅ Email sent to {to_email}: {subject}")

    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")

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
