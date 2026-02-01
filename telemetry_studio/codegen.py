from telemetry_studio.data_models import ProjectDefinition, MessageDefinition, FieldDefinition

class CodeGenerator:
    def __init__(self, project: ProjectDefinition):
        self.project = project

    def generate_enums(self) -> str:
        lines = ["from enum import IntEnum", "", ""]
        for enum_def in self.project.enums:
            lines.append(f"class {enum_def.name}(IntEnum):")
            if not enum_def.items:
                lines.append("    pass")
            for item in enum_def.items:
                lines.append(f"    {item.name} = {item.value}")
            lines.append("")
        return "\n".join(lines)

    def generate_messages(self) -> str:
        lines = [
            "from serializer_core import *",
            "from .enums import *", 
            "",
            ""
        ]
        
        for msg in self.project.messages:
            if msg.active_configs:
                for cfg in msg.active_configs:
                    lines.append(f"@register(system_config_id='{cfg}')")
            else:
                lines.append("@register") 
                
            lines.append(f"class {msg.name}(Message):")
            
            if not msg.fields:
                lines.append("    pass")
            
            for field in msg.fields:
                ftype_map = {
                    "Enum": "EnumField",
                    "String": "StringField",
                    "FixedPoint": "FixedPointField",
                    "Array": "ArrayField",
                    "BitField": "BitField"
                }
                backend_type = ftype_map.get(field.field_type, field.field_type)
                
                opts_str = self._format_options(field)
                lines.append(f"    {field.name} = {backend_type}({opts_str})")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_options(self, field: FieldDefinition) -> str:
        args = []
        opts = field.options.copy()
        
        if field.field_type == "BitField":
            bits = opts.pop("bits", [])
            bit_strs = [f"Bit({b['width']}, '{b['name']}')" for b in bits]
            args.append(f"[{', '.join(bit_strs)}]")
            # Base type default is UInt32, usually fine to omit if default
            
        elif field.field_type == "Enum":
             enum_name = opts.pop("enum_name", "MyEnum")
             args.append(enum_name) # First arg is enum_cls
             args.append("UInt8") # Second arg is base_type
             
        elif field.field_type == "Array":
             # ArrayField(item_type, mode, count...)
             # We need to constructing item_type object from options?
             # For now, let's assume simple primitive array or fix for demo
             # The demo uses ArrayField(UInt16(), ...) logic? 
             # No, ArrayConfigDialog logic is complex.
             # For now, just fix 'Array' -> 'UInt8()' default to avoid crash
             args.append("UInt8()")
             
        if "active_configs" in opts and not opts["active_configs"]:
            del opts["active_configs"] 
            
        for k, v in opts.items():
            if k == "count_field" and opts.get("mode") == "Fixed": continue
            
            if isinstance(v, str):
                args.append(f"{k}='{v}'")
            else:
                args.append(f"{k}={v}")
                
        return ", ".join(args)
