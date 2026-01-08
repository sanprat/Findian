import sys
import os
import struct
from datetime import datetime

# Add project root to sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.binary_parser import BinaryParser

def create_mock_mode_2_packet():
    """ Creates a byte string mimicking a SmartAPI Mode 2 packet """
    
    # Structure (Little Endian <)
    # 1B sub_mode
    # 1B exch_type
    # 25B token (utf-8)
    # 8B seq_num
    # 8B timestamp
    # 8B ltp
    # 8B ltq
    # 8B atp
    # 8B vol
    # 8B buy_q
    # 8B sell_q
    # 8B open
    # 8B high
    # 8B low
    # 8B close
    
    sub_mode = 2
    exch_type = 1
    token = "3045".ljust(25, '\x00').encode('utf-8') # SBI token example
    seq_num = 1001
    
    # Time: Now
    ts_ms = int(datetime.utcnow().timestamp() * 1000)
    
    # Prices (multiplied by 100)
    ltp = 50050 # 500.50
    ltq = 10
    atp = 50000
    vol = 1500000
    buy_q = 500000
    sell_q = 400000
    open_p = 49500
    high_p = 50500
    low_p = 49000
    close_p = 49800
    
    # Pack
    # Format: B B 25s q q q q q q q q q q q q
    # Total: 1+1+25 + 8*10 = 27 + 80 = 107 bytes (Wait, 130?)
    # The parser expects 8*10 = 80 bytes of data after header
    # Let's match the parser logic exactly
    
    data = struct.pack(
        '<B B 25s q q q q q q q q q q q q',
        sub_mode,
        exch_type,
        token,
        seq_num,
        ts_ms,
        ltp,
        ltq,
        atp,
        vol,
        buy_q,
        sell_q,
        open_p,
        high_p,
        low_p,
        close_p
    )
    
    return data

def test_parser():
    print("🧪 Testing Binary Parser with Mock Data...")
    
    packet = create_mock_mode_2_packet()
    print(f"📦 Created mock packet of size: {len(packet)} bytes")
    
    parsed = BinaryParser.parse_mode_2(packet)
    
    if parsed:
        print("✅ Parsing Successful:")
        print(f"   Token: {parsed['token']}")
        print(f"   LTP: {parsed['ltp']} (Expected 500.5)")
        print(f"   Volume: {parsed['volume']}")
        print(f"   Open: {parsed['open']}")
        print(f"   High: {parsed['high']}")
        print(f"   Close: {parsed['close']}")
        
        assert parsed['ltp'] == 500.5, "LTP Mismatch"
        assert parsed['volume'] == 1500000, "Volume Mismatch"
        print("✨ Assertions Passed!")
    else:
        print("❌ Parsing Failed")

if __name__ == "__main__":
    test_parser()
