import unittest
from tests.common import KitchenSinkString, Status
import struct

class TestStringFields(unittest.TestCase):
    def test_string_formatting(self):
        obj = KitchenSinkString()
        obj.msg_id = 99
        obj.cmd_type = "TEST"
        obj.cmd_str = "KITCHEN"
        obj.label = "MYLABEL"
        obj.description = "DESC"
        obj.desc_len = 4 # Helper
        obj.status = Status.ERROR # Enum String?
        
        # StringMessage.serialize() constructs framing:
        # <MSG_ID|CMD_TYPE|CMD_STR|FIELDS...>
        # MSG_ID is from obj.msg_id?
        # KitchenSinkString has msg_id field.
        # StringMessage uses self.msg_id attribute for header. 
        # If msg_id field exists, update attribute? 
        # Usually StringMessage logic is:
        # header uses `self.msg_id` (int). 
        # body uses `self.fields`.
        # If `msg_id` is ALSO a field, it might appear in body?
        # KitchenSinkString has `msg_id` as first field.
        # StringMessage.serialize iterates fields (skipping cmd_type, cmd_str).
        # So `msg_id` (body) will be serialized as field 1.
        
        data = obj.serialize()
        s_data = data.decode('utf-8')
        print(f"DEBUG: {s_data}")
        
        # Check Start/End
        self.assertTrue(s_data.startswith('<'))
        self.assertTrue(s_data.endswith('>'))
        
        # Parse Header components (assuming defaults)
        # <ID|TYPE:CMD:MSG_ID;LABEL;DESC_LEN;DESC;STATUS;...CHKSUM>
        
        # Check substrings
        self.assertIn("TEST", s_data)
        self.assertIn("KITCHEN", s_data)
        self.assertIn("MYLABEL", s_data)
        self.assertIn("DESC", s_data)
        
        # Verify Msg ID in body (as UInt8 -> primitive to string?)
        # UInt8.to_string() falls back to str(val).
        self.assertIn("99", s_data)

    def test_deserialize_string(self):
        # Construct valid string
        # Assuming defaults:
        # <0063|TEST:KITCHEN:99;REQ       ;4;DESC;ERROR;CHKSUM>
        # Note: Fixed String "MYLABEL" (10 chars) -> "MYLABEL\x00\x00\x00" ? 
        # StringField.to_string() for Fixed mode usually pads or returns as is?
        # V2: `to_string` logic for Fixed? 
        # If generic `str(val)`, no padding.
        # If `StringField` overrides `to_string`?
        
        # Let's rely on valid input simulation.
        # Deserialize
        # Construct valid string with PIPE delimiters (Defaults)
        # <0063|TEST|KITCHEN|HEAD;99;REQ...
        # 0063 (ID) | TEST (Type) | KITCHEN (Cmd) | HEAD (Head) | 99 (MsgID); REQ... (Body)
        # Note: head is first Body field. msg_id is second.
        raw_string = "<0063|TEST|KITCHEN|HEAD;99;MYLABEL   ;4;DESC;ERROR;00>"
        data = raw_string.encode('utf-8')
        
        # Deserialize
        # Use from_bytes directly as Message.deserialize is not defined
        obj, consumed = KitchenSinkString.from_bytes(data)
        
        self.assertIsInstance(obj, KitchenSinkString)
        self.assertEqual(obj.cmd_type, "TEST")
        self.assertEqual(obj.cmd_str, "KITCHEN")
        self.assertEqual(obj.msg_id, 99)
        # Fixed string usually whitespace stripped or null stripped?
        # StringField.from_bytes (String Protocol)?
        # Actually StringMessage deserialization splits by DELIM_FIELD.
        # Then calls `from_string` (implied)?
        # `StringMessage.deserialize_string` calls `msg_cls.from_bytes(data)`.
        # `StringMessage.from_bytes` (implied or inherited?)
        # `Message` doesn't have `from_string`.
        # `StringMessage` implements `from_bytes` by splitting and assigning?
        # Let's check `StringMessage.from_bytes` implementation in next step if needed.
        # For now, simplistic assertions.
        
if __name__ == '__main__':
    unittest.main()
