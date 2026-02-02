import sys
import os
import unittest
from enum import Enum

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from serializer_core import *
from serializer_core.string_message import StringMessage
from serializer_core.protocols import ProtocolConfig

# Define Enums if needed
class LogLevel(Enum):
    INFO = 1
    WARN = 2
    ERROR = 3

@register
class StringLogMsg(StringMessage):
    protocol_mode = "string"
    cmd_type = StringField(default='RET', size_mode='Dynamic', length=10, encoding='utf-8')
    cmd_str = StringField(default='PING', size_mode='Dynamic', length=10, encoding='utf-8')

class TestStringProtocol(unittest.TestCase):
    def setUp(self):
        # Reset Config with specific delimiters to verify strict format
        ProtocolConfig.configure(
            start="<", end=">", 
            delim_field=";", 
            delim_id="|", delim_type="^", delim_cmd="@", # Mixed delimiters
            use_checksum=True
        )

    def test_serialization(self):
        msg = StringLogMsg()
        
        data = msg.serialize()
        print(f"Serialized: {data}")
        
        # Format: <MSG_ID><D_ID><CMD_TYPE><D_TYPE><CMD><D_CMD><FIELDS...><CS><END>
        # MSG_ID: 00A1
        # CMD_TYPE: LOG
        # CMD: SYS
        # Fields: 100;WARN;BatteryLow
        # Checksum: Calculated over <00A1|LOG^SYS@100;WARN;BatteryLow;
        
        # Verify headers manually since checksum is variable
        s_data = data.decode('utf-8')
        
        self.assertTrue(s_data.startswith("<00A1|LOG^SYS@"))
        self.assertIn("100;WARN;BatteryLow;", s_data)
        self.assertTrue(s_data.endswith(">"))
        
        # Test Checksum existence (last 2 chars before >)
        chk = s_data[-3:-1]
        self.assertTrue(chk.isalnum()) # Hex

    def test_deserialization(self):
        # Construct a raw message matching the format
        # MSG_ID=00FF, TYPE=LOG, CMD=SYS, Seq=999, Level=ERROR, Msg=Fatal
        # Delimiters: | ^ @ ;
        # Body: 999;ERROR;Fatal;
        
        # To make checksum pass easily, we can disable checksum in config for this test or calc it?
        # Let's enable checksum but just use a "valid" string if possible from serialize?
        
        msg_out = StringLogMsg()
        msg_out.msg_id = 255
        msg_out.seq = 999
        msg_out.level = LogLevel.ERROR
        msg_out.msg = "Fatal"
        
        data = msg_out.serialize()
        
        # Deserialize
        msg_in, length = Registry.deserialize(data)
        
        self.assertIsInstance(msg_in, StringLogMsg)
        self.assertEqual(msg_in.msg_id, 255)
        self.assertEqual(msg_in.cmd_type, "LOG")
        self.assertEqual(msg_in.cmd_str, "SYS")
        self.assertEqual(msg_in.seq, 999)
        self.assertEqual(msg_in.level.name, "ERROR")
        self.assertEqual(msg_in.msg, "Fatal")

if __name__ == '__main__':
    unittest.main()
