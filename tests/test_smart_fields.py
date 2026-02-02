import sys
import os
import struct
import time
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from serializer_core import *
from serializer_core.checksums import crc16

@register
class SmartMsg(Message):
    # Header
    sync = UInt8(default=0xAA)
    
    # Checksum covering 'payload_a' to 'payload_b'
    # 2 bytes. 0x0000 placeholder initially.
    checksum = UInt16(is_checksum=True, algorithm='CRC16', start_field='payload_a', end_field='payload_b')
    
    # Timestamp (Auto-injected)
    ts = UInt32(is_timestamp=True, resolution='s')
    
    # Payload
    payload_a = UInt8(default=0x01)
    payload_b = UInt8(default=0x02) # End field included? implementation detail implies yes?

class TestSmartFields(unittest.TestCase):
    def test_smart_fields(self):
        msg = SmartMsg()
        data = msg.serialize()
        
        print(f"Serialized Hex: {data.hex()}")
        
        # Verify Length
        # Sync(1) + Checksum(2) + BS(4) + A(1) + B(1) = 9 bytes
        self.assertEqual(len(data), 9)
        
        # Verify Timestamp (approx)
        ts_val = struct.unpack('<I', data[3:7])[0]
        now = int(time.time())
        print(f"Timestamp in packet: {ts_val}, Now: {now}")
        self.assertTrue(abs(ts_val - now) <= 1)
        
        # Verify Checksum
        # Payload A (0x01) + Payload B (0x02)
        # CRC16 ([0x01, 0x02])
        # Manually calc
        expected_crc = crc16(bytes([0x01, 0x02]))
        print(f"Expected CRC16(01 02): {hex(expected_crc)}")
        
        actual_crc_bytes = data[1:3]
        actual_crc = struct.unpack('<H', actual_crc_bytes)[0]
        print(f"Actual CRC in packet: {hex(actual_crc)}")
        
        self.assertEqual(actual_crc, expected_crc)

if __name__ == '__main__':
    unittest.main()
