import logging
import asyncio
import json
import threading
from typing import List, Dict, Set, Optional
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from app.core.binary_parser import BinaryParser
from app.core.cache import cache

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages multiple SmartAPI WebSocket V2 connections to handle token limits.
    """
    def __init__(self, api_credentials: List[Dict]):
        """
        api_credentials: List of dicts {auth_token, api_key, client_code, feed_token}
        """
        self.credentials = api_credentials
        self.connections: List[SmartWebSocketV2] = []
        self.subscription_map: List[Set[str]] = [] # Maps connection index to set of tokens
        self.is_running = False
        self._ws_instances = []  # Store instances for subscription

    def _on_data(self, wsapp, message):
        """Callback for incoming WebSocket data"""
        try:
            # SmartWebSocketV2 provides parsed data as dict
            if isinstance(message, dict):
                # Extract relevant fields
                token = message.get('token')
                ltp = message.get('last_traded_price') or message.get('ltp')
                volume = message.get('volume_trade_for_the_day', 0)
                
                if token and ltp:
                    # Get symbol from token
                    from app.core.symbol_tokens import get_symbol
                    symbol = get_symbol(str(token))
                    
                    if symbol:
                        # Store in Redis
                        try:
                            cache.hset(f"stock:{symbol}", mapping={
                                "ltp": str(ltp),
                                "volume": str(volume),
                                "timestamp": str(message.get('exchange_timestamp', 'now')),
                                "token": str(token)
                            })
                            logger.debug(f"📊 {symbol}: ₹{ltp}")
                        except Exception as redis_err:
                            logger.error(f"Redis storage failed for {symbol}: {redis_err}")
                    
        except Exception as e:
            logger.error(f"Error processing WS data: {e}")

    def _on_open(self, wsapp):
        logger.info("✅ SmartWebSocketV2 Connected")

    def _on_close(self, wsapp):
        logger.warning("⚠️ SmartWebSocketV2 Closed")

    def _on_error(self, wsapp, error):
        logger.error(f"❌ SmartWebSocketV2 Error: {error}")

    def start(self):
        """Initialize and start all connections in background threads"""
        logger.info(f"Starting {len(self.credentials)} WebSocket V2 connections...")
        
        def start_connection(i, creds):
            """Start a single WebSocket connection in a thread"""
            try:
                # Initialize SmartWebSocketV2
                sws = SmartWebSocketV2(
                    creds['auth_token'],
                    creds['api_key'],
                    creds['client_code'],
                    creds['feed_token']
                )
                
                # Assign callbacks
                sws.on_data = self._on_data
                sws.on_open = self._on_open
                sws.on_close = self._on_close
                sws.on_error = self._on_error
                
                # Connect (blocking call, runs in this thread)
                sws.connect()
                
            except Exception as e:
                logger.error(f"Failed to start connection {i+1}: {e}")
        
        for i, creds in enumerate(self.credentials):
            # Start each connection in its own daemon thread
            thread = threading.Thread(
                target=start_connection,
                args=(i, creds),
                daemon=True,
                name=f"SmartWS-{i+1}"
            )
            thread.start()
            self.subscription_map.append(set())
            logger.info(f"Connection {i+1} thread started.")
            
            # Small delay between connections
            import time
            time.sleep(0.5)

        self.is_running = True
        logger.info(f"✅ All {len(self.credentials)} WebSocket threads started")

    def subscribe(self, tokens: List[str], mode=2): # mode 1=LTP, 2=Quote, 3=Snap Quote
        """
        Distribute tokens across available connections.
        SmartAPI V2 limit per conn is ~1000-3000 depending on plan.
        """
        if not self.connections:
            logger.error("No active connections to subscribe")
            return

        # Simple logic: Add to the connection with fewest subscriptions
        current_token_idx = 0
        
        while current_token_idx < len(tokens):
            # Find connection with minimum tokens
            lens = [len(s) for s in self.subscription_map]
            min_idx = lens.index(min(lens))
            
            # Subscribe in batches
            chunk_size = 50
            chunk = tokens[current_token_idx : current_token_idx + chunk_size]
            
            # Create subscription packet for V2
            # Exchange Type: 1 (NSE), 2 (NFO)... Assuming NSE Equity (1)
            token_list = [{
                "exchangeType": 1,
                "tokens": chunk
            }]
            
            try:
                correlation_id = f"pystock_bot_{min_idx}"
                self.connections[min_idx].subscribe(
                    correlation_id=correlation_id,
                    mode=mode,
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
