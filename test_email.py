#!/usr/bin/env python3
"""
Email Configuration Test Script
Tests SMTP connection and email sending functionality
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load from environment or use defaults
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_USERNAME)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", SENDER_EMAIL)

def test_smtp_connection():
    """Test SMTP server connection and authentication"""
    print("=" * 60)
    print("📧 EMAIL CONFIGURATION TEST")
    print("=" * 60)
    
    # Display configuration
    print("\n🔧 Configuration:")
    print(f"  SMTP Server: {SMTP_SERVER}")
    print(f"  SMTP Port: {SMTP_PORT}")
    print(f"  SMTP Username: {SMTP_USERNAME}")
    print(f"  SMTP Password: {'*' * len(SMTP_PASSWORD) if SMTP_PASSWORD else 'NOT SET'}")
    print(f"  Sender Email: {SENDER_EMAIL}")
    print(f"  Admin Email: {ADMIN_EMAIL}")
    
    # Check for missing credentials
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("\n❌ ERROR: Missing SMTP credentials!")
        print("  Set SMTP_USERNAME and SMTP_PASSWORD environment variables.")
        return False
    
    if not ADMIN_EMAIL:
        print("\n⚠️  WARNING: ADMIN_EMAIL not set, using SENDER_EMAIL")
    
    # Test connection
    print("\n🔌 Testing SMTP Connection...")
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        print("  ✅ Connected to SMTP server")
        
        # Test STARTTLS
        print("\n🔐 Testing STARTTLS...")
        server.starttls()
        print("  ✅ TLS connection established")
        
        # Test authentication
        print("\n🔑 Testing Authentication...")
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        print("  ✅ Authentication successful")
        
        # Send test email
        print(f"\n📨 Sending test email to {ADMIN_EMAIL}...")
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = ADMIN_EMAIL
        msg["Subject"] = "Pystock Email Test - Configuration Verified"
        
        body = f"""
This is a test email from your Pystock application.

If you're reading this, your email configuration is working correctly! ✅

Configuration Details:
- SMTP Server: {SMTP_SERVER}:{SMTP_PORT}
- Sender: {SENDER_EMAIL}
- Recipient: {ADMIN_EMAIL}
- Timestamp: {os.popen('date').read().strip()}

Next Steps:
1. Check your spam/junk folder if you don't see this email
2. Mark as "Not Spam" to ensure future emails arrive in your inbox
3. Add {SENDER_EMAIL} to your contacts

---
Sent from Pystock Email Test Script
"""
        msg.attach(MIMEText(body, "plain"))
        
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, ADMIN_EMAIL, text)
        print("  ✅ Test email sent successfully!")
        
        server.quit()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print(f"\n📬 Check your inbox at: {ADMIN_EMAIL}")
        print("⚠️  If you don't see it, check your SPAM/JUNK folder!")
        print("\n")
        
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n❌ Authentication Failed: {e}")
        print("\nPossible causes:")
        print("  1. Incorrect username or password")
        print("  2. Gmail App Password expired or invalid")
        print("  3. 2-Factor Authentication not enabled")
        print("\nSolution:")
        print("  • Generate a new App Password at: https://myaccount.google.com/apppasswords")
        print("  • Ensure 2FA is enabled on your Google account")
        return False
        
    except smtplib.SMTPException as e:
        print(f"\n❌ SMTP Error: {e}")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test_smtp_connection()
    exit(0 if success else 1)
