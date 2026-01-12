"""
SmartAPI Authentication Manager
Handles session creation, TOTP generation, and token management for Angel One SmartAPI.
"""
import logging
import pyotp
from typing import Dict, Optional
from SmartApi import SmartConnect

logger = logging.getLogger(__name__)


class SmartApiAuth:
    """Manages authentication and session for SmartAPI"""
    
    def __init__(self, api_key: str, client_code: str, pin: str, totp_secret: str):
        """
        Initialize SmartAPI Auth Manager
        
        Args:
            api_key: Angel One API Key
            client_code: Client Code (User ID)
            pin: Login PIN/Password
            totp_secret: TOTP Secret from QR Code
        """
        self.api_key = api_key
        self.client_code = client_code
        self.pin = pin
        self.totp_secret = totp_secret
        
        self.smart_api: Optional[SmartConnect] = None
        self.jwt_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        self.is_authenticated = False
    
    def get_totp(self) -> str:
        """Generate current TOTP using pyotp"""
        try:
            totp = pyotp.TOTP(self.totp_secret)
            return totp.now()
        except Exception as e:
            logger.error(f"Failed to generate TOTP: {e}")
            raise
    
    def login(self) -> bool:
        """
        Authenticate with SmartAPI and retrieve tokens
        
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            logger.info(f"🔐 Attempting SmartAPI login for {self.client_code}...")
            
            # Initialize SmartConnect
            self.smart_api = SmartConnect(api_key=self.api_key)
            
            # Generate TOTP
            totp = self.get_totp()
            
            # Generate Session
            data = self.smart_api.generateSession(
                clientCode=self.client_code,
                password=self.pin,
                totp=totp
            )
            
            if not data or data.get('status') == False:
                logger.error(f"❌ SmartAPI Login Failed: {data}")
                return False
            
            # Extract tokens
            session_data = data.get('data', {})
            self.jwt_token = session_data.get('jwtToken')
            self.refresh_token = session_data.get('refreshToken')
            
            # Get feed token
            self.feed_token = self.smart_api.getfeedToken()
            
            if not all([self.jwt_token, self.refresh_token, self.feed_token]):
                logger.error("❌ Failed to retrieve all required tokens")
                return False
            
            self.is_authenticated = True
            logger.info(f"✅ SmartAPI Login Successful for {self.client_code}")
            logger.info(f"📡 Feed Token: {self.feed_token[:10]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ SmartAPI Login Exception: {e}")
            self.is_authenticated = False
            return False
    
    def refresh_session(self) -> bool:
        """
        Refresh the session using refresh token
        
        Returns:
            bool: True if refresh successful
        """
        try:
            if not self.smart_api or not self.refresh_token:
                logger.warning("⚠️ Cannot refresh: No active session or refresh token")
                return False
            
            logger.info("🔄 Refreshing SmartAPI session...")
            
            new_token = self.smart_api.generateToken(self.refresh_token)
            
            if new_token and new_token.get('status'):
                self.jwt_token = new_token.get('data', {}).get('jwtToken')
                logger.info("✅ Session refreshed successfully")
                return True
            else:
                logger.error(f"❌ Session refresh failed: {new_token}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Session refresh exception: {e}")
            return False
    
    def get_tokens(self) -> Dict[str, str]:
        """
        Get all authentication tokens
        
        Returns:
            dict: Dictionary containing all tokens
        """
        return {
            'jwt_token': self.jwt_token,
            'refresh_token': self.refresh_token,
            'feed_token': self.feed_token,
            'api_key': self.api_key,
            'client_code': self.client_code
        }
    
    def logout(self) -> bool:
        """
        Terminate the SmartAPI session
        
        Returns:
            bool: True if logout successful
        """
        try:
            if self.smart_api:
                result = self.smart_api.terminateSession(self.client_code)
                logger.info(f"👋 Logged out from SmartAPI: {result}")
                self.is_authenticated = False
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Logout failed: {e}")
            return False
