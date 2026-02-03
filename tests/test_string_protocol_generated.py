import sys
import os
import unittest
import struct

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from serializer_core import *
from serializer_core.protocols import ProtocolConfig

# Target Module to Test
TARGET_MODULE = 'tests.msg_str'

try:
    import tests.msg_str as M
    print(f"Successfully imported {TARGET_MODULE}")
except ImportError:
    print(f"{TARGET_MODULE} not found. Using internal mock.")
    import types
    M = types.ModuleType('mock_messages')
    
    @register
    class StringLogMsg(StringMessage):
        protocol_mode = "string"
        cmd_type = StringField(default='TYPE', is_discriminator=True)
        cmd_str = StringField(default='CMD', is_discriminator=True)
    M.StringLogMsg = StringLogMsg

class TestGeneratedMessages(unittest.TestCase):
    def setUp(self):
        # Configure String Protocol just in case
        ProtocolConfig.configure(
            start="<", end=">", 
            delim_field=";", 
            delim_id="|", delim_type="|", delim_cmd="|",
            use_checksum=True
        )

    def test_generated_messages(self):
        """Iterate over all Message subclasses in the imported module and test them."""
        found_any = False
        
        # Filter for Message classes defined in M
        candidates = []
        for name, cls in vars(M).items():
            if isinstance(cls, type) and issubclass(cls, Message) and cls is not Message and cls is not StringMessage:
                candidates.append((name, cls))
                
        if not candidates:
            self.fail(f"No Message subclasses found in {TARGET_MODULE} to test.")

        print(f"\nFound {len(candidates)} messages to test in {TARGET_MODULE}")
        
        for name, cls in candidates:
            with self.subTest(msg=name):
                print(f"\n--- Testing Message: {name} ---")
                self.verify_message_lifecycle(cls)
                found_any = True

    def verify_message_lifecycle(self, msg_cls):
        # 1. Instantiate
        msg = msg_cls()
        msg.msg_id = 0x01 # Set a dummy ID if it exists? 
        # Actually msg_id is usually handled by Registry lookup for binary, 
        # but for StringMessage it's part of the header if we use the header fields.
        
        # Check Protocol Mode
        mode = getattr(msg_cls, 'protocol_mode', 'binary')
        print(f"Protocol Mode: {mode}")
        
        # 2. Serialize
        try:
            data = msg.serialize()
        except Exception as e:
            self.fail(f"Serialization failed for {msg_cls.__name__}: {e}")
            
        print(f"Serialized Data: {data}")
        
        # 3. Verification of Output Format
        if mode == 'string':
            # Should look like bytes: b'<...>'
            self.assertTrue(data.startswith(b'<'), f"String message should start with '<', got {data}")
            self.assertTrue(data.endswith(b'>'), f"String message should end with '>', got {data}")
        else:
            # Binary checks?
            # msg1 in msg_str.py is binary but has string fields.
            # Serialization of StringField in binary mode:
            # It packs the string based on its encoding and length (if fixed) or just the bytes if dynamic?
            # StringField without size_mode defaults to fixed? No, code gen defaults.
            pass

        # 4. Deserialize
        # We use Registry.deserialize(data).
        # Note: If multiple messages have receiving discriminators, this might pick the wrong one 
        # if they are identical.
        try:
            parsed_msg, len_ = Registry.deserialize(data)
        except Exception as e:
            self.fail(f"Deserialization failed for {msg_cls.__name__}: {e}")

        # 5. Compare
        self.assertIsNotNone(parsed_msg, "Deserialization returned None")
        self.assertIsInstance(parsed_msg, msg_cls, f"Deserialized type mismatch. Needed {msg_cls}, got {type(parsed_msg)}")
        
        # Field Comparison
        for name, field in msg_cls.fields.items():
            val_orig = getattr(msg, name)
            val_new = getattr(parsed_msg, name)
            
            # Rough equality check
            self.assertEqual(val_orig, val_new, f"Field '{name}' mismatch: {val_orig} != {val_new}")

        print(f"Verified {msg_cls.__name__} Round-Trip OK.")

if __name__ == '__main__':
    unittest.main()
