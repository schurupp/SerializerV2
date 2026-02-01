from telemetry_studio.data_models import ProjectDefinition, MessageDefinition, FieldDefinition, EnumDefinition, EnumItem
from telemetry_studio.codegen import CodeGenerator

def test_codegen():
    print("--- Testing Code Generator ---")
    
    proj = ProjectDefinition()
    
    # 1. Enums
    e = EnumDefinition("Status", [EnumItem("OK", 0), EnumItem("ERROR", 1)])
    proj.enums.append(e)
    
    # 2. Messages
    m = MessageDefinition("Telemetry")
    
    # Discriminator
    f1 = FieldDefinition("msg_id", "UInt8", {"is_discriminator": True, "default": 0x10})
    m.fields.append(f1)
    
    # String
    f2 = FieldDefinition("label", "StringField", {"size_mode": "Fixed", "length": 16})
    m.fields.append(f2)
    
    # Enum
    f3 = FieldDefinition("status", "EnumField", {"enum_name": "Status"})
    m.fields.append(f3)
    
    # BitField
    f4 = FieldDefinition("flags", "BitField", {"bits": [{'name': 'enabled', 'width': 1}, {'name': 'mode', 'width': 3}]})
    m.fields.append(f4)
    
    proj.messages.append(m)
    
    # Generate
    gen = CodeGenerator(proj)
    
    print(">>> ENUMS.PY <<<")
    print(gen.generate_enums())
    
    print("\n>>> MESSAGES.PY <<<")
    print(gen.generate_messages())

if __name__ == "__main__":
    test_codegen()
