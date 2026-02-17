import xml.etree.ElementTree as ET
import os
from typing import Dict, Any, List, Optional
from telemetry_studio.data_models import (
    ProjectDefinition, MessageDefinition, FieldDefinition, 
    EnumDefinition, EnumItem, SPLDefinition
)

class XMLImporter:
    def __init__(self):
        self.project = None
        self.enums = [] # List of EnumDefinition
        self.messages = [] # List of MessageDefinition
        self.warnings = []
        
    def import_xml(self, file_path: str) -> ProjectDefinition:
        """Parses the XML and returns a ProjectDefinition."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"XML file not found: {file_path}")
            
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        if root.tag != "System":
            raise ValueError("Root element must be <System>")
            
        # 1. System Level Attributes
        # Project Attributes
        sys_id = root.get("Id", "NewSystem")
        endianness = root.get("Endianness", "little") 
        project_endian = "Little"
        if endianness.lower() == 'big': project_endian = "Big"
        
        # Parse SPL Configs
        # SPLConfigs="Config_A,Config A;Config_B,Config B"
        spl_str = root.get("SPLConfigs", "")
        spl_configs = []
        if spl_str:
            for pair in spl_str.split(";"):
                if "," in pair:
                    parts = pair.split(",")
                    spl_configs.append(SPLDefinition(name=parts[0].strip()))
                elif pair.strip():
                    spl_configs.append(SPLDefinition(name=pair.strip()))

        self.project = ProjectDefinition(
            name=sys_id,
            protocol_mode="binary", 
            global_endianness=project_endian,
            spl_configs=spl_configs
        )
        # (Assuming internal enums list is empty initially)
        
        # 2. Iterate SubSystems
        for subsystem in root.findall("SubSystem"):
            self._parse_subsystem(subsystem)
            
        self.project.messages = self.messages
        self.project.enums = self.enums
        return self.project

    def _parse_subsystem(self, subsystem: ET.Element):
        cat_id = subsystem.get("Id", "Default")
        inv_bits = subsystem.get("InverseBitFields", "false").lower() == "true"
        # If InverseBitFields is true, default bit_order for this category's messages could be MSB?
        # Specification says: "If 'true', set default bit_order='MSB' for child BitFields"
        
        for msg_node in subsystem.findall("SimpleMessage"):
            self._parse_message(msg_node, category=cat_id, default_bit_order="MSB" if inv_bits else "LSB")

    def _parse_message(self, msg_node: ET.Element, category: str, default_bit_order: str):
        msg_id = msg_node.get("Id")
        display_name = msg_node.get("DisplayName", msg_id)
        
        # Discriminator Parsing
        disc_ref = msg_node.get("Discriminator", "")
        discriminator_field_name = None
        if disc_ref.startswith("@"):
            discriminator_field_name = disc_ref[1:]
            
        msg_endian_str = msg_node.get("Endianness")
        msg_endian = None
        if msg_endian_str:
            msg_endian = 'Big' if msg_endian_str.lower() == 'big' else 'Little'
            
        # Variants (SPL)
        variants_str = msg_node.get("Variants", "")
        spl_tags = []
        if variants_str:
             spl_tags = [v.strip() for v in variants_str.split(',') if v.strip()]
            
        # Parse Children
        fields = []
        
        # Helper to get variants
        def get_variants(node):
            v = node.get("Variants", "")
            if v: return v.split(",")
            return []

        for child in msg_node:
            f_defs = self._parse_field_node(child, f"{msg_id}", default_bit_order)
            for f_def in f_defs:
                # Check for discriminator
                if discriminator_field_name and f_def.name == discriminator_field_name:
                    f_def.options['is_discriminator'] = True
                    
                # Active Configs (SPL)
                # Note: Variants are processed inside _parse_field_node for StructField
                # But for top level, check current child variants if not already set?
                # _parse_field_node already attaches variants if found on the node?
                # Actually, I should check child.get("Variants") here? 
                # But I'm iterating `child`. 
                # _parse_field_node handles extracting from `node`.
                # Wait, my previous code extracted variants in loop.
                # I should let _parse_field_node handle it or pass it.
                # Let's verify: In previous code, I called `get_variants(child)` inside the loop.
                # Now _parse_field_node should handle it for consistenct.
                
                # Re-apply variants if not present?
                if 'active_configs' not in f_def.options:
                    variants = get_variants(child)
                    if variants: f_def.options['active_configs'] = variants
                    
                fields.append(f_def)
                
        # Create Message Definition
        # Naming: {category}_{msg_id} to avoid collision? 
        # User said: "Id -> Class Name". But also "Id -> Category prefix".
        # "Use as a 'Category' prefix for imported messages (e.g., interfaceId_messageId1)"
        full_name = f"{category}_{msg_id}"
        
        msg_def = MessageDefinition(
            name=full_name,
            fields=fields,
            endianness=msg_endian,
            active_configs=spl_tags
        )
        # Note: MessageDefinition might need 'endianness' attribute update if not present.
        # It currently has fields. It is a dataclass.
        # We inject endianness into the definition if supported.
        # Wait, MessageDefinition in data_models.py needs to support endianness.
        
        if hasattr(msg_def, 'options'):
             # If MessageDefinition has options dict
             pass
        else:
             # Just set attribute
             msg_def.endianness = msg_endian
             
        self.messages.append(msg_def)

    def _parse_field_node(self, node: ET.Element, prefix_scope: str, default_bit_order: str) -> List[FieldDefinition]:
        tag = node.tag
        f_id = node.get("Id")
        f_type = node.get("Type")
        repeat = node.get("Repeat")
        
        common_opts = {}
        # Endianness override
        endian = node.get("Endianness")
        if endian:
            common_opts['byte_order'] = '>' if endian.lower() == 'big' else '<'
            
        # Default Value
        default_val = node.get("DefaultValue")
        if default_val is not None:
             # Try convert later based on type
             common_opts['default'] = default_val
             
        field_def = None
        
        # 1. Primitive Field
        if tag == "Field":
            # Map type u1..u8, s1..s8, f4..f8, bool
            py_type = self._map_primitive_type(f_type)
            
            # Auto-Length
            if node.get("PresetMessageLength", "false").lower() == "true":
                common_opts['is_length'] = True
                begin = node.get("PresetMessageLengthBegin", "")
                end = node.get("PresetMessageLengthEnd", "")
                if begin.startswith("@"): begin = begin[1:]
                if end.startswith("@"): end = end[1:]
                common_opts['start_field'] = begin
                common_opts['end_field'] = end
            
            field_def = FieldDefinition(name=f_id, field_type=py_type, options=common_opts)
            
        # 2. SequentialBitFields
        elif tag == "SequentialBitFields":
            # Container for BitField
            # Parse children
            bits = []
            for sub in node.findall("SingleSequentialBitField"):
                bits.append({
                    'name': sub.get("Id"),
                    'width': int(sub.get("BitCount", 1)),
                    'data_type': self._map_primitive_type(sub.get("Type", "u4"), simple=True), # f4 -> UInt usually
                    'default_value': 0 # Not specified in example
                })
            
            # Type of container usually matches ByteCount
            byte_count = int(node.get("ByteCount", 4))
            # Map to suitable base type
            base_map = {1: 'UInt8', 2: 'UInt16', 4: 'UInt32', 8: 'UInt64'}
            base_type = base_map.get(byte_count, 'UInt32')
            
            common_opts['bits'] = bits
            common_opts['bit_order'] = default_bit_order # From SubSystem
            
            field_def = FieldDefinition(name=f_id, field_type="BitField", options=common_opts)
            # BitField uses 'base_type' implicitly? No, BitField wrapper needs it?
            # Our current UI doesn't explicitly ask for base type (defaults to UInt32/dynamic?),
            # but backend `BitField` checks `base_type`.
            # We might need to add `base_type` to options if we want to support it correctly.
            # But `BitField` init takes `base_type`.
            
        # 3. EnumField
        elif tag == "EnumField":
            enum_name = f"{prefix_scope}_{f_id}"
            items = []
            for item in node.findall("Enumerator"):
                val_str = item.get("Value")
                # Int or String? XML usually implies Int unless String Enum?
                # "Type" attr on EnumField is usually storage type (u8).
                val = int(val_str)
                items.append(EnumItem(name=item.get("Id"), value=val))
            
            enum_def = EnumDefinition(name=enum_name, storage_type=self._map_primitive_type(f_type), items=items)
            self.enums.append(enum_def)
            
            common_opts['enum_name'] = enum_name
            field_def = FieldDefinition(name=f_id, field_type="Enum", options=common_opts)

        # 4. StringField
        elif tag == "StringField":
            length_attr = node.get("Length", "10")
            if length_attr.startswith("@"):
                common_opts['size_mode'] = 'Dynamic'
                common_opts['length_field'] = length_attr[1:]
            else:
                common_opts['size_mode'] = 'Fixed'
                common_opts['length'] = int(length_attr)
            
            common_opts['encoding'] = 'utf-8' # Default
            field_def = FieldDefinition(name=f_id, field_type="String", options=common_opts)
            
        # 5. ChecksumField
        elif tag == "ChecksumField":
            # Map Algo
            algo_map = {"CRC16": "CRC16"} # Expand logic
            common_opts['is_checksum'] = True
            common_opts['algorithm'] = algo_map.get(node.get("Algorithm"), "CRC16")
            
            start = node.get("StartFieldId", "")
            end = node.get("EndFieldId", "")
            if start.startswith("@"): start = start[1:]
            if end.startswith("@"): end = end[1:]
            common_opts['start_field'] = start
            common_opts['end_field'] = end
            
            # Type determines storage
            py_type = self._map_primitive_type(f_type)
            field_def = FieldDefinition(name=f_id, field_type=py_type, options=common_opts)

        # 6. StructField (Nested) -> FLATTENED as per User Request
        elif tag == "StructField":
            # Flatten subfields into the current list.
            # Ignore Id? (It vanishes).
            # What about Repeat? (Ignored/Flattened).
            # What about Variants? (Propagate to children).
            
            parent_variants = node.get("Variants", "")
            p_vars = parent_variants.split(",") if parent_variants else []
            
            sub_results = []
            for child in node:
                # Recursively parse
                children_defs = self._parse_field_node(child, prefix_scope, default_bit_order)
                
                for c_def in children_defs:
                    # Apply parent variants logic: Intersection or Union?
                    # Usually intersection: If parent is Config_B, children are only valid in Config_B.
                    # If child has its own Variants, it must be valid in both.
                    if p_vars:
                        current_vars = c_def.options.get("active_configs", [])
                        if current_vars:
                            # Intersection
                            new_vars = [v for v in current_vars if v in p_vars]
                            if not new_vars:
                                # Conflict essentially means field never exists?
                                continue 
                            c_def.options["active_configs"] = new_vars
                        else:
                            # Apply parent's constraints
                            c_def.options["active_configs"] = p_vars
                    
                    sub_results.append(c_def)
            
            return sub_results
            
        if not field_def:
            return []
            
        # Correct Convert Default Value Types
        if 'default' in common_opts:
            d = common_opts['default']
            if field_def.field_type in ["UInt8", "UInt16", "UInt32", "UInt64", "Int8", "Int16", "Int32", "Int64"]:
                 try: 
                     # Support Hex (0x...) and Decimal
                     common_opts['default'] = int(d, 0)
                 except: pass
            elif field_def.field_type in ["Float", "Double"]:
                 try: common_opts['default'] = float(d)
                 except: pass
            elif field_def.field_type == "Bool":
                 common_opts['default'] = (d.lower() == "true")
        
        # Wrap in Array if Repeat present
        if repeat:
            array_opts = {}
            if repeat.startswith("@"):
                array_opts['mode'] = 'Dynamic'
                array_opts['count_field'] = repeat[1:]
            else:
                array_opts['mode'] = 'Fixed'
                array_opts['count'] = int(repeat)
            
            inner_def = field_def
            # IMPORTANT: ArrayField wraps the definition.
            # But here we are returning a FieldDefinition.
            # We need to transform this `field_def` into an Array definition.
            
            # Since FieldDefinition doesn't support nested definition object directly,
            # We assume backend initialization logic handles 'item_type' as a string or handled via options.
            # For primitives/enums/strings, it works.
            
            field_def = FieldDefinition(
                name=f_id,
                field_type="Array",
                options={
                    **array_opts,
                    "item_type": inner_def.field_type,
                    "item_options": inner_def.options 
                }
            )

        return [field_def]

    def _map_primitive_type(self, xml_type: str, simple=False) -> str:
        # u1..u8 -> Bytes?
        # u1 = 1 byte = UInt8
        # u2 = 2 bytes = UInt16
        # u4 = 4 bytes = UInt32
        # u8 = 8 bytes = UInt64
        mapping = {
            "u1": "UInt8", "u2": "UInt16", "u4": "UInt32", "u8": "UInt64",
            "s1": "Int8", "s2": "Int16", "s4": "Int32", "s8": "Int64",
            "f4": "Float", "f8": "Double",
            "bool": "Bool"
        }
        res = mapping.get(xml_type)
        if simple and "Float" in res: return "UInt32" # Fallback for bitfield bits
        return res
