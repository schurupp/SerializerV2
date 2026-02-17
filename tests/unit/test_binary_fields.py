import unittest
import struct
from tests.common import KitchenSinkBinary, Color, NestedStruct, fuzz_binary
from serializer_core import BitField, Bit, UInt8, UInt16, UInt32, Int16, FixedPointField, Float32, Float64

class TestBinaryFields(unittest.TestCase):
    def test_endianness(self):
        obj = KitchenSinkBinary()
        # Magic is Big Endian UInt16 -> 0xCAFE -> b'\xCA\xFE'
        # Default is Little Endian.
        # Let's verify via serialization (without using full loop if possible, or partial)
        # We can inspect the field definitions packing if accessible, but better to use obj.serialize()
        
        # We need to minimally populate to serialize
        fuzz_binary(obj)
        
        # Set expected values BEFORE serialize
        obj.u16_val = 0x1234
        
        data = obj.serialize()
        print(f"DEBUG: Data Length: {len(data)}")
        print(f"DEBUG: Data Hex: {data.hex()}")
        
        # Check First 2 bytes (Magic)
        self.assertEqual(data[0:2], b'\xCA\xFE')
        # Offset calculation is hard without parsing whole thing.
        # But we know magic (2) + version (1) + u8_val (1) + u16_val (2) location.
        # 2+1+1 = 4. 
        # data[4:6] should be b'\x34\x12'
        val_offset = 2 + 1 + 1
        self.assertEqual(data[val_offset:val_offset+2], b'\x34\x12')

    def test_bitfields_lsb(self):
        # LSB Container: enable(1), mode(3), color(4)
        obj = KitchenSinkBinary()
        # Assign dict
        obj.flags_lsb = {
            'enable': True,
            'mode': 5,
            'color': Color.BLUE # 3
        }
        
        # Expected:
        # 1 | (5 << 1) | (3 << 4) = 1 | 10 | 48 = 59
        
        # We need to minimally populate to serialize
        fuzz_binary(obj)
        # Re-set target verify
        obj.flags_lsb = {'enable': True, 'mode': 5, 'color': Color.BLUE}
        
        data = obj.serialize()
        # Offset 46.
        self.assertEqual(data[46], 59)

    def test_bitfields_msb(self):
        # MSB Container: valid(1), reserved(7)
        obj = KitchenSinkBinary()
        obj.flags_msb = {
            'valid': True, # 1
            'reserved': 0x0F # 15
        }
        
        # Expected: (1 << 7) | 15 = 128 + 15 = 143
        
        fuzz_binary(obj)
        obj.flags_msb = {'valid': True, 'reserved': 0x0F}
        
        data = obj.serialize()
        # Offset 47.
        self.assertEqual(data[47], 143)

    def test_fixed_point(self):
        obj = KitchenSinkBinary()
        fuzz_binary(obj)
        
        # fp_u: Q8.8 Unsigned (Scale 256)
        # Val = 12.5 -> 12.5 * 256 = 3200
        obj.fp_u = 12.5
        
        # fp_s: Q7.8 Signed (Scale 256)
        # Val = -5.0 -> -5.0 * 256 = -1280
        obj.fp_s = -5.0
        
        data = obj.serialize()
        # Offsets?
        # Header (46) + LSB(1) + MSB(1) = 48.
        # fp_u is at 48 (2 bytes).
        # fp_s is at 50 (2 bytes).
        
        # unpack UInt16 LE
        raw_u = struct.unpack('<H', data[48:50])[0]
        self.assertEqual(raw_u, 3200)
        
        # unpack Int16 LE
        raw_s = struct.unpack('<h', data[50:52])[0]
        self.assertEqual(raw_s, -1280)
        
    def test_smart_fields(self):
        obj = KitchenSinkBinary()
        fuzz_binary(obj)
        
        # Set array to known size to predict lengths
        obj.scores = [1, 2, 3, 4] # 4 bytes
        obj.items = [] # 0 bytes dynamic
        obj.item_count = 0 
        
        # Structure Size:
        # Header (46 primitives + 2 bitfield + 6 FixedPoint) = 54 bytes.
        # Scores (4 bytes) = 58.
        # item_count (2 bytes) = 60.
        # items (0) = 60.
        # ts (8 bytes, as UInt64) = 68.
        # msg_len (2) = 70.
        # crc (2) = 72.
        
        msg_len = UInt16(is_length=True, start_field='magic', end_field='items') 
        # ...
        data = obj.serialize()
        
        # Check Length
        # Start 'magic': 0.
        # End 'items': 60.
        # Expected Length = 60.
        
        # msg_len is at 68.
        len_val = struct.unpack('<H', data[68:70])[0]
        self.assertEqual(len_val, 60)
        
if __name__ == '__main__':
    unittest.main()
