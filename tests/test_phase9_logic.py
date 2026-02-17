
import unittest
import queue
from collections import deque
from serializer_core.stream import StreamHandler
from serializer_core.registry import Registry
from telemetry_studio.codegen import CodeGenerator
from telemetry_studio.data_models import ProjectDefinition, MessageDefinition, FieldDefinition, EnumDefinition, EnumItem
from telemetry_studio.importers.xml_importer import XMLImporter
import os

class TestPhase9Logic(unittest.TestCase):
    
    def test_stream_handler_strictness(self):
        # 1. Test BINARY mode strictness
        handler = StreamHandler(protocol_mode="BINARY")
        dq = deque()
        # Feed garbage that isn't a valid binary message
        handler.feed(b'\x01\x02\x03', dq)
        self.assertEqual(len(dq), 0, "Should not deserialize garbage in Binary mode")
        
        # 2. Test STRING mode strictness (mock)
        # We need to register a string message to test this properly? 
        # Or just ensure it calls Registry.deserialize_string and doesn't crash on binary garbage
        handler_str = StreamHandler(protocol_mode="STRING")
        handler_str.feed(b'\x01\x02\x03', dq) 
        # Should likely fail silently or print error, but NOT use binary deserializer logic
        self.assertEqual(len(dq), 0)

    def test_codegen_defaults_binary(self):
        # EnumField default should be int (0) in Binary Mode
        proj = ProjectDefinition(name="TestProj")
        msg = MessageDefinition(name="TestMsg", protocol_mode="binary")
        enum_field = FieldDefinition(
            name="status", 
            field_type="Enum", 
            options={"enum_name": "Status", "default": 0} 
        )
        msg.fields.append(enum_field)
        proj.messages.append(msg)
        
        gen = CodeGenerator(proj)
        code = gen.generate_messages()
        
        # Expect: status = EnumField(..., default=0) -> default=0
        self.assertIn("default=0", code)
        self.assertNotIn("default='0'", code)

    def test_codegen_defaults_string(self):
        # EnumField default should be string ('OK') in String Mode
        proj = ProjectDefinition(name="TestProj")
        msg = MessageDefinition(name="TestMsg", protocol_mode="string")
        enum_field = FieldDefinition(
            name="status", 
            field_type="Enum", 
            options={"enum_name": "Status", "default": "OK"} 
        )
        msg.fields.append(enum_field)
        proj.messages.append(msg)
        
        gen = CodeGenerator(proj)
        code = gen.generate_messages()
        
        # Expect: status = EnumField(..., default='OK')
        self.assertIn("default='OK'", code)

    def test_xml_importer_variants(self):
        # Create a temp XML file
        xml_content = """<System Id="TestSys">
            <SubSystem Id="Sub1">
                <SimpleMessage Id="Msg1" Variants="ConfigA, ConfigB">
                    <Field Id="F1" Type="u4" />
                </SimpleMessage>
            </SubSystem>
        </System>"""
        
        filename = "test_variants.xml"
        with open(filename, "w") as f:
            f.write(xml_content)
            
        try:
            importer = XMLImporter()
            proj = importer.import_xml(filename)
            msg = proj.messages[0]
            
            self.assertIn("ConfigA", msg.active_configs)
            self.assertIn("ConfigB", msg.active_configs)
        finally:
            if os.path.exists(filename):
                os.remove(filename)

if __name__ == '__main__':
    unittest.main()
