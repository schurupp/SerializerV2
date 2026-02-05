import unittest
from tests.common import KitchenSinkBinary, KitchenSinkString, fuzz_binary, fuzz_string

class TestKitchenSink(unittest.TestCase):
    def test_binary_loop(self):
        for i in range(10): # Run 10 times
            original = KitchenSinkBinary()
            fuzz_binary(original)
            
            data = original.serialize()
            
            # Method 1: Use classmethod from_bytes
            reconstructed, _ = KitchenSinkBinary.from_bytes(data)
            
            # Verify fields
            self.assertEqual(original.u8_val, reconstructed.u8_val)
            self.assertEqual(original.u64_val, reconstructed.u64_val)
            self.assertEqual(original.s32_val, reconstructed.s32_val)
            self.assertAlmostEqual(original.f4_val, reconstructed.f4_val, places=4)
            self.assertEqual(original.bool_val, reconstructed.bool_val)
            
            # Bitfields
            self.assertEqual(original.flags_lsb['enable'], reconstructed.flags_lsb['enable'])
            self.assertEqual(original.flags_lsb['mode'], reconstructed.flags_lsb['mode'])
            # Enum check might compare Enum value vs Int if not cast
            # original.color is Color.GREEN. reconstructed... depends on if Bit() definition has enum mapping?
            # Bit definition in common.py: Bit(4, 'color', 'Enum', enum_name='Color')
            # Backend: BitField.from_bytes returns dict. 
            # Does it convert to Enum?
            # Inspecting BitField.from_bytes... it returns raw values from shifting.
            # It does NOT use enum mapping (based on my memory of fields.py view).
            # So reconstructed will be Int (3). Original is Color.GREEN (3).
            # Equality should pass.
            self.assertEqual(original.flags_lsb['color'], reconstructed.flags_lsb['color'])
            
            self.assertEqual(original.flags_msb['valid'], reconstructed.flags_msb['valid'])
            self.assertEqual(original.flags_msb['reserved'], reconstructed.flags_msb['reserved'])
            
            # Fixed Point
            self.assertAlmostEqual(original.fp_u, reconstructed.fp_u, delta=0.1) 
            self.assertAlmostEqual(original.fp_s, reconstructed.fp_s, delta=0.01)
            self.assertAlmostEqual(original.fp_dm, reconstructed.fp_dm, delta=0.01)
            
            # Arrays
            self.assertEqual(list(original.scores), list(reconstructed.scores))
            self.assertEqual(len(original.items), len(reconstructed.items))
            for k, item in enumerate(original.items):
                self.assertEqual(item.id, reconstructed.items[k].id)
                self.assertAlmostEqual(item.value, reconstructed.items[k].value, places=4)
                
            # Smart Fields
            # Timestamp (might drift if auto-set on creation vs deserialization)
            # Both set manually/auto? 
            # If `is_timestamp` writes current time on serialize, 
            # logic usually: `serialize` updates `ts`. `deserialize` reads it.
            # So `reconstructed.ts` should equal `original.ts` (which was updated during serialize).
            # But `original.serialize()` modified `original` in place? 
            # Yes, standard behavior.
            self.assertEqual(original.ts, reconstructed.ts)
            
            # CRC and Length (calculated)
            # Reconstructed should have correct values read from stream.
            self.assertEqual(original.msg_len, reconstructed.msg_len)
            self.assertEqual(original.crc, reconstructed.crc)

    def test_string_loop(self):
        for i in range(10):
            original = KitchenSinkString()
            fuzz_string(original)
            
            # Handle Dependencies manually if needed (desc_len)
            # If backend auto-updates, great. If not, manual.
            # Usually dynamic string needs length field set.
            if original.description:
                original.desc_len = len(original.description)
                
            data = original.serialize()
            
            reconstructed, _ = KitchenSinkString.from_bytes(data)
            
            self.assertEqual(original.head, reconstructed.head)
            self.assertEqual(original.msg_id, reconstructed.msg_id)
            # Label fixed width, might have padding.
            self.assertTrue(reconstructed.label.startswith(original.label.strip())) 
            self.assertEqual(original.description, reconstructed.description)
            self.assertEqual(original.status, reconstructed.status)
            
            # Checksum
            self.assertEqual(original.chk, reconstructed.chk)

if __name__ == '__main__':
    unittest.main()
