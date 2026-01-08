import logging
import asyncio
import json
import threading
from typing import List, Dict, Set
from SmartApi.smartStream import SmartStream
from app.core.binary_parser import BinaryParser
from app.core.cache import cache

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages multiple SmartAPI WebSocket connections to handle token limits.
    """
    def __init__(self, api_credentials: List[Dict]):
        """
        api_credentials: List of dicts {api_key, client_code, password, token, feed_token}
        """
        self.credentials = api_credentials
        self.connections: List[SmartStream] = []
        self.subscription_map: List[Set[str]] = [] # Maps connection index to set of tokens
        self.is_running = False

    def _on_data(self, ws, payload, is_binary, channel_number):
        """Callback for incoming WebSocket data"""
        try:
            if is_binary:
                # payload is memoryview or bytes
                parsed_data = BinaryParser.parse_mode_2(bytes(payload))
                if parsed_data:
                    # Async dispatch to Redis/Processors
                    # Since we are in a thread callback, we need to be careful with async
                    # For high performance, we push to a local queue or directly to Redis if synchronous
                    
                    # For this implementation, we'll try to push to Redis via a helper
                    # Or print for now to verify logic
                    pass
                    # logger.debug(f"Tick: {parsed_data['token']} -> {parsed_data['ltp']}")
                    
        except Exception as e:
            logger.error(f"Error processing WS data: {e}")

    def _on_open(self, ws):
        logger.info("✅ SmartAPI WebSocket Connected")

    def _on_close(self, ws):
        logger.warning("⚠️ SmartAPI WebSocket Closed")

    def _on_error(self, ws, error):
        logger.error(f"❌ SmartAPI WebSocket Error: {error}")

    def start(self):
        """Initialize and start all connections"""
        logger.info(f"Starting {len(self.credentials)} WebSocket connections...")
        
        for i, creds in enumerate(self.credentials):
            try:
                # Initialize SmartStream
                # Note: Adjust args based on strict library version 
                sws = SmartStream(
                    creds['client_code'],
                    creds['password'],
                    creds['api_key'],
                    creds['token'],
                    creds['feed_token']
                )
                
                # Assign callbacks
                sws.on_data = lambda ws, payload, is_bin, ch=i: self._on_data(ws, payload, is_bin, ch)
                sws.on_open = self._on_open
                sws.on_close = self._on_close
                sws.on_error = self._on_error
                
                # Connect
                sws.connect()
                
                self.connections.append(sws)
                self.subscription_map.append(set())
                logger.info(f"Connection {i+1} initialized.")
                
            except Exception as e:
                logger.error(f"Failed to start connection {i+1}: {e}")

        self.is_running = True

    def subscribe(self, tokens: List[str], mode="LTP_QUOTE"): # CMP=1, Quote=2
        """
        Distribute tokens across available connections.
        SmartAPI limit per conn is often ~1000-3000 depending on plan.
        We load balance simply round-robin or fill-first.
        """
        if not self.connections:
            logger.error("No active connections to subscribe")
            return

        # Simple logic: Add to the connection with fewest subscriptions
        current_token_idx = 0
        
        while current_token_idx < len(tokens):
            # Find loop with minimum tokens
            lens = [len(s) for s in self.subscription_map]
            min_idx = lens.index(min(lens))
            
            # Simple chunking
            chunk_size = 50 # Subscribe in batches
            chunk = tokens[current_token_idx : current_token_idx + chunk_size]
            
            # Create subscription packet
            # Exchange Type: 1 (NSE), 2 (NFO)... Assuming all NSE Equity (1) for now
            token_list = [{"exchangeType": 1, "tokens": t} for t in chunk]
            
            try:
                self.connections[min_idx].subscribe(
                    correlation_id="stock_alert_bot",
                    mode=2, # Quote Mode
                    token_list=token_list
                )
                self.subscription_map[min_idx].update(chunk)
                logger.info(f"Subscribed {len(chunk)} tokens on Conn {min_idx+1}")
            except Exception as e:
                logger.error(f"Subscription failed on Conn {min_idx+1}: {e}")
                
            current_token_idx += chunk_size

    def stop(self):
        for conn in self.connections:
            conn.close()
        self.is_running = False
