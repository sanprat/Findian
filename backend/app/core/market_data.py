import os
import logging
import pyotp
from NorenRestApiPy.NorenApi import NorenApi

logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self):
        self.api = NorenApi(host='https://api.shoonya.com/NorenWClientTP/', websocket='wss://api.shoonya.com/NorenWSTP/')
        self.user_id = os.getenv("FINVASIA_USER_ID")
        self.password = os.getenv("FINVASIA_PASSWORD")
        self.token = os.getenv("FINVASIA_TOKEN")
        self.totp_key = os.getenv("FINVASIA_TOTP_KEY")
        self.vendor_code = os.getenv("FINVASIA_VENDOR_CODE")
        self.imei = os.getenv("FINVASIA_IMEI")
        self.is_connected = False

    def login(self):
        """
        Logs in to Finvasia using the credentials and auto-generated TOTP.
        """
        try:
            if not self.totp_key:
                logger.error("FINVASIA_TOTP_KEY is missing!")
                return False

            # 1. Generate TOTP
            totp = pyotp.TOTP(self.totp_key)
            current_otp = totp.now()

            # 2. Login
            ret = self.api.login(
                userid=self.user_id,
                password=self.password,
                twoFA=current_otp,
                vendor_code=self.vendor_code,
                api_secret=self.token,
                imei=self.imei
            )

            if ret and ret.get('stat') == 'Ok':
                self.is_connected = True
                logger.info(f"✅ Finvasia Login Successful. Token: {ret.get('susertoken')}")
                return True
            else:
                logger.error(f"❌ Finvasia Login Failed: {ret.get('emsg')}")
                return False

        except Exception as e:
            logger.error(f"❌ Login Critical Error: {str(e)}")
            return False

    def get_quote(self, symbol: str, exchange: str = "NSE"):
        """
        Fetch live quote (LTP) for a symbol.
        """
        if not self.is_connected:
            if not self.login():
                return None

        # Search for the scrip first to get token
        search = self.api.searchscrip(exchange=exchange, searchtext=symbol)
        
        if search and len(search) > 0:
            # Assume first match is correct (Improve this later)
            token = search[0]['token']
            
            # Get Quote
            # NorenApi uses different methods for Rest vs Websocket. 
            # For MVP, we use REST snapshot.
            quote = self.api.get_quotes(exchange=exchange, token=token)
            
            if quote and quote.get('stat') == 'Ok':
                return {
                    "symbol": symbol,
                    "ltp": float(quote.get('lp', 0)),
                    "volume": int(quote.get('v', 0)),
                    "close": float(quote.get('c', 0)),
                    # Add more fields as needed for indicators
                }
        
        return None
