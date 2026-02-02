from telemetry_studio.data_models import ProjectDefinition, MessageDefinition, FieldDefinition

class CodeGenerator:
    def __init__(self, project: ProjectDefinition):
        self.project = project

    def generate_enums(self, target_config: str = None) -> str:
        lines = ["from enum import IntEnum", "", ""]
        for enum_def in self.project.enums:
            # SPL Filtering
            if target_config and enum_def.active_configs:
                if target_config not in enum_def.active_configs:
                    continue
                    
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
            
            base_cls = "Message"
            if getattr(msg, 'protocol_mode', 'binary') == 'string':
                base_cls = "StringMessage"
                
            lines.append(f"class {msg.name}({base_cls}):")
            
            if getattr(msg, 'protocol_mode', 'binary') == 'string':
                 lines.append(f'    protocol_mode = "string"')
            
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
        
        # Helper keys to exclude from generic kwargs
        exclude_keys = ["active_configs", "bits", "enum_name", "storage_type", "item_type"] 
        
        if field.field_type == "BitField":
            bits = opts.pop("bits", [])
            bit_strs = []
            for b in bits:
                # Bit(width, name, [data_type, default, enum...])
                # Bit class: __init__(width, name, data_type, default_value, enum_name)
                # To be precise we should output args. 
                # Bit(1, 'foo', data_type='Bool', default_value=0)
                # Let's simple format:
                b_args = [str(b['width']), f"'{b['name']}'"]
                if "data_type" in b: b_args.append(f"data_type='{b['data_type']}'")
                if "default_value" in b: b_args.append(f"default_value={b['default_value']}")
                if "enum_name" in b and b['enum_name']: b_args.append(f"enum_name='{b['enum_name']}'")
                
                bit_strs.append(f"Bit({', '.join(b_args)})")
                
            args.append(f"[{', '.join(bit_strs)}]")
            
        elif field.field_type == "Enum":
             enum_name = opts.pop("enum_name", "MyEnum")
             stor_type = opts.pop("storage_type", "UInt8")
             args.append(enum_name) # enum_cls
             args.append(f"storage_type='{stor_type}'")
             
        elif field.field_type == "Array":
             # Placeholder for Array: ArrayField(UInt8())
             args.append("UInt8()")
             
        # Active Configs cleanup
        if "active_configs" in opts and not opts["active_configs"]:
            del opts["active_configs"]
        
        if field.field_type == "String":
             if opts.get("size_mode") == "Dynamic":
                 if "length" in opts: del opts["length"]
             if opts.get("encoding") == "utf-8":
                 del opts["encoding"]

        # Generic Kwargs
        for k, v in opts.items():
            if k in exclude_keys: continue
            if k == "count_field" and opts.get("mode") == "Fixed": continue
            if k == "byte_order" and v == "<": continue # Skip default Little Endian
            
            if isinstance(v, str):
                args.append(f"{k}='{v}'")
            else:
                args.append(f"{k}={v}")
                
        return ", ".join(args)
