import sys
import os
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from serializer_core import *
from serializer_core.protocols import ProtocolConfig

# Attempt to import generated messages
TARGET_MODULE = 'tests.Messages'

try:
    import tests.Messages as M
    print(f"Successfully imported {TARGET_MODULE}")
except ImportError:
    print(f"{TARGET_MODULE} not found. Using internal mock.")
    import types
    M = types.ModuleType('mock_messages')
    
    @register
    class StringLogMsg(StringMessage):
        protocol_mode = "string"
        cmd_type = StringField(default='TYPE', size_mode='Dynamic')
        cmd_str = StringField(default='CMD', size_mode='Dynamic')
    M.StringLogMsg = StringLogMsg

class TestGeneratedStringProtocol(unittest.TestCase):
    def setUp(self):
        ProtocolConfig.configure(
            start="<", end=">", 
            delim_field=";", 
            delim_id="|", delim_type="|", delim_cmd="|",
            use_checksum=True
        )

    def test_all_generated_messages(self):
        """Iterate over all StringMessage subclasses in the imported module and test them."""
        found_any = False
        
        for name, cls in vars(M).items():
            if isinstance(cls, type) and issubclass(cls, StringMessage) and cls is not StringMessage:
                found_any = True
                with self.subTest(msg=name):
                    print(f"\nTesting Generated Message: {name}")
                    self.verify_message_lifecycle(cls)
        
        if not found_any:
            self.fail("No StringMessage subclasses found in generated code to test.")

    def verify_message_lifecycle(self, msg_cls):
        msg = msg_cls()
        msg.msg_id = 0x01
        
        # Serialize
        data = msg.serialize()
        print(f"  Serialized: {data}")
        
        # Deserialize
        parsed_msg, len_ = Registry.deserialize(data)
        
        self.assertIsInstance(parsed_msg, msg_cls)
        
        # Basic field check
        if hasattr(msg, 'cmd_type'):
            self.assertEqual(parsed_msg.cmd_type, msg.cmd_type)
        if hasattr(msg, 'cmd_str'):
            self.assertEqual(parsed_msg.cmd_str, msg.cmd_str)
            
        print(f"  Verified {msg_cls.__name__} successfully.")

if __name__ == '__main__':
    unittest.main()
