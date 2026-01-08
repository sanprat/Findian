import struct
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BinaryParser:
    """
    Parses binary packets from Angel One SmartAPI WebSocket V2 (Smart Stream).
    Focus is on Mode 2 (Quote) packets.
    """

    @staticmethod
    def parse_mode_2(binary_data):
        """
        Parse Mode 2 (Quote) packet.
        Structure (Little Endian):
        - Subscription Mode (1 byte)
        - Exchange Type (1 byte)
        - Token (25 bytes)
        - Sequence Number (8 bytes)
        - Exchange Timestamp (8 bytes)
        - LTP (8 bytes)
        - Open (8 bytes)
        - High (8 bytes)
        - Low (8 bytes)
        - Close (8 bytes)
        - Volume (8 bytes)
        - Snapshot Best Buy/Sell (variable, but Mode 2 main fields end here usually)
        
        Note: The actual SmartAPI binary layout can vary. This implementation 
        uses the struct format for the standard Quote packet (130 bytes approx).
        """
        try:
            # Basic validation
            if not binary_data:
                return None

            # Unpack Header
            # Subscription Mode (1 byte)
            subscription_mode = binary_data[0]
            
            # Exchange Type (1 byte)
            exchange_type = binary_data[1]
            
            # Token (25 bytes) - Null terminated or padded
            token_raw = binary_data[2:27]
            token = token_raw.decode('utf-8').replace('\x00', '')
            
            # Sequence Number (8 bytes) - long long
            sequence_number = struct.unpack('<q', binary_data[27:35])[0]
            
            # Exchange Timestamp (8 bytes) - long long (epoch milliseconds)
            exchange_timestamp_raw = struct.unpack('<q', binary_data[35:43])[0]
            exchange_timestamp = datetime.fromtimestamp(exchange_timestamp_raw / 1000.0)
            
            # LTP (8 bytes) - long long (in paise, divide by 100)
            ltp_raw = struct.unpack('<q', binary_data[43:51])[0]
            ltp = ltp_raw / 100.0
            
            # Keep reading for Mode 2 specific fields if packet length allows
            # Mode 2 usually adds OHLC and Volume
            # Offset 51 starts LTQ? No, let's assume standard Q position
            
            # Based on SmartAPI V2 Spec for Quote (Mode 2):
            # ... LTP (8), LTQ (8), ATP (8), Volume (8), Total Buy Qty (8), Total Sell Qty (8), Open (8), High (8), Low (8), Close (8) ...
            
            # Let's map dynamically based on documentation logic:
            # We strictly need LTP, Volume, and OHLC.
            
            # Current Pointer
            offset = 43 
            
            # LTP
            ltp = struct.unpack('<q', binary_data[offset:offset+8])[0] / 100.0
            offset += 8
            
            # Last Traded Qty 
            ltq = struct.unpack('<q', binary_data[offset:offset+8])[0]
            offset += 8
            
            # Avg Traded Price
            atp = struct.unpack('<q', binary_data[offset:offset+8])[0] / 100.0
            offset += 8
            
            # Volume
            volume = struct.unpack('<q', binary_data[offset:offset+8])[0]
            offset += 8
            
            # Total Buy Qty
            total_buy_qty = struct.unpack('<q', binary_data[offset:offset+8])[0]
            offset += 8
            
            # Total Sell Qty
            total_sell_qty = struct.unpack('<q', binary_data[offset:offset+8])[0]
            offset += 8
            
            # Open
            open_price = struct.unpack('<q', binary_data[offset:offset+8])[0] / 100.0
            offset += 8
            
            # High
            high_price = struct.unpack('<q', binary_data[offset:offset+8])[0] / 100.0
            offset += 8
            
            # Low
            low_price = struct.unpack('<q', binary_data[offset:offset+8])[0] / 100.0
            offset += 8
            
            # Close
            close_price = struct.unpack('<q', binary_data[offset:offset+8])[0] / 100.0
            offset += 8
            
            return {
                "token": token,
                "exchange_type": exchange_type,
                "timestamp": exchange_timestamp,
                "ltp": ltp,
                "volume": volume,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "atp": atp,
                "parsed_at": datetime.utcnow()
            }
            
        except struct.error as e:
            logger.error(f"Binary parse error (struct): {e}")
            return None
        except Exception as e:
            logger.error(f"Binary parse error (general): {e}")
            return None
