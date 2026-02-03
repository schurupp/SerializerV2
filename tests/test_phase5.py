import unittest
import struct
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from serializer_core.messages import Message, register
from serializer_core.fields import UInt16, UInt32
from serializer_core.registry import Registry

# 1. Test Hierarchical Endianness
@register
class LittleMsg(Message):
    endianness = '<'
    f1 = UInt16() # Should be Little
    f2 = UInt32(byte_order='>') # Explicit Big

@register
class BigMsg(Message):
    endianness = '>'
    f1 = UInt16() # Should be Big
    f2 = UInt32(byte_order='<') # Explicit Little

# 2. Test __repr__
@register
class ReprMsg(Message):
    endianness = '<'
    a = UInt16()
    b = UInt16()

class TestPhase5(unittest.TestCase):
    def test_endianness(self):
        # LittleMsg
        lm = LittleMsg(f1=0x1234, f2=0x12345678)
        data = lm.serialize()
        # f1: 34 12 (Little)
        # f2: 12 34 56 78 (Big)
        self.assertEqual(data[0:2], b'\x34\x12') 
        self.assertEqual(data[2:6], b'\x12\x34\x56\x78')
        
        # BigMsg
        bm = BigMsg(f1=0x1234, f2=0x12345678)
        data = bm.serialize()
        # f1: 12 34 (Big)
        # f2: 78 56 34 12 (Little)
        self.assertEqual(data[0:2], b'\x12\x34')
        self.assertEqual(data[2:6], b'\x78\x56\x34\x12')

    def test_repr(self):
        msg = ReprMsg(a=10, b=20)
        s = repr(msg)
        print(f"\nRepr Output: {s}")
        self.assertIn("ReprMsg", s)
        self.assertIn("a=10", s)
        self.assertIn("b=20", s)

    def test_string_memoryview_fix(self):
        # Setup Registry with String Config
        from serializer_core.protocols import ProtocolConfig
        ProtocolConfig.configure(start="<", end=">")
        
        # Test Case: Registry.deserialize with memoryview
        # We need to trigger the startswith check logic.
        # Since we don't have a registered string message for this test easily,
        # we can just invoke deserialize and check it doesn't crash on startswith.
        # It might return Unknown Message, but NOT AttributeError.
        
        data = b"<START>"
        mv = memoryview(data)
        
        try:
             Registry.deserialize(mv)
        except Exception as e:
             # Should NOT be AttributeError: 'memoryview' ... has no attribute 'startswith'
             # print(f"\nCaught Expected Exception: {type(e).__name__}: {e}")
             self.assertNotIsInstance(e, AttributeError)
             # It likely raises struct.error or similar because no message matches

if __name__ == '__main__':
    unittest.main()
