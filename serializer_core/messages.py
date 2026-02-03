import struct
from typing import Dict, Any, List, Tuple
from .fields import Field, PrimitiveField
from .registry import Registry

class Message:
    """Base class for all messages."""
    fields: Dict[str, Field] = {}
    _packing_plan: List[Any] = []
    _struct_size: int = 0
    _active_configs: List[str] = [] # SPL Tags
    
    def __init__(self, **kwargs):
        for name, field in self.fields.items():
            if name in kwargs:
                setattr(self, name, kwargs[name])
            elif field.default is not None:
                setattr(self, name, field.default)
            else:
                 setattr(self, name, None)

    def __repr__(self):
        parts = []
        for name in self.fields.keys():
            val = getattr(self, name, None)
            parts.append(f"{name}={repr(val)}")
        return f"{self.__class__.__name__}({', '.join(parts)})"

    def serialize(self) -> bytes:
        from . import checksums
        import time
        chunks = []
        checksum_patches = [] # (checksum_field_name, field_obj, offset_in_struct)
        length_patches = []
        
        # 1. Pass 1: Pack data and identify checksums/lengths
        current_offset = 0
        field_info = {} # name -> {'start': int, 'size': int}

        for step in self._packing_plan:
            action, payload = step
            if action == 'struct':
                fmt, field_names, struct_obj = payload
                values = []
                
                chunk_start_offset = current_offset
                local_offset = 0
                
                for name in field_names:
                    field = self.fields[name]
                    val = getattr(self, name)
                    
                    # Store logic size
                    f_size = field._struct.size
                    field_info[name] = {'start': chunk_start_offset + local_offset, 'size': f_size}
                    
                    field_info[name] = {'start': chunk_start_offset + local_offset, 'size': f_size}
                    
                    # Checksum Placeholders
                    if field.is_checksum:
                        checksum_patches.append({
                            'name': name,
                            'field': field,
                            'offset': chunk_start_offset + local_offset
                        })
                        val = 0 # Placeholder
                    
                    # Length Placeholders
                    elif field.is_length:
                        length_patches.append({
                            'name': name,
                            'field': field,
                            'offset': chunk_start_offset + local_offset
                        })
                        val = 0 # Placeholder
                        
                    # Timestamp Injection
                    
                    # Timestamp Injection
                    elif field.is_timestamp:
                        t = time.time()
                        # Check resolution property.
                        # Since PrimitiveField uses kwargs, attribute might not exist on Field base.
                        # But we modified Field to accept kwargs.
                        # So it should be there. default to 's'
                        res = getattr(field, 'resolution', 's')
                        if res == 'ms':
                            t *= 1000
                        val = int(t)
                    
                    # Normal packing logic
                    else:
                        if hasattr(val, 'value'): # Enum
                            val = val.value
                        if val is None:
                            val = 0
                    
                    values.append(val)
                    
                    local_offset += f_size
                    
                chunks.append(struct_obj.pack(*values))
                current_offset += struct_obj.size
                
            elif action == 'complex':
                field_name = payload
                field = self.fields[field_name]
                
                val = getattr(self, field_name)
                # Checksum not supported inside complex field (yet)
                
                chunk = field.to_bytes(val)
                chunks.append(chunk)
                
                chunk_len = len(chunk)
                field_info[field_name] = {'start': current_offset, 'size': chunk_len}
                current_offset += chunk_len

        # 2. Join buffer
        buffer = bytearray(b''.join(chunks))

        # 3. Pass 2: Apply Patches
        field_offsets = {name: info['start'] for name, info in field_info.items()}
        
        # 3. Pass 2: Apply Patches (Lengths then Checksums)
        
        # 2a. Apply Lengths
        for patch in length_patches:
            name = patch['name']
            field = patch['field']
            offset = patch['offset']
            
            start_field = getattr(field, 'start_field', None)
            end_field = getattr(field, 'end_field', None)
            
            if start_field and end_field:
                start_info = field_info.get(start_field)
                end_info = field_info.get(end_field)
                
                if start_info and end_info:
                    start_byte = start_info['start']
                    # Convention: Inclusive of end field size?
                    # Common pattern: Length of Payload.
                    # Payload = [StartField ... EndField]
                    end_byte = end_info['start'] + end_info['size']
                    
                    calc_len = end_byte - start_byte
                    if calc_len < 0: calc_len = 0
                    
                    # Pack into buffer
                    if hasattr(field, '_struct'):
                        field._struct.pack_into(buffer, offset, calc_len)
                        
        # 2b. Apply Checksums
        for patch in checksum_patches:
            name = patch['name']
            field = patch['field']
            offset = patch['offset'] # Offset of the checksum field itself
            
            # Get config from field (algorithm, start_field, end_field)
            algo_name = getattr(field, 'algorithm', 'CRC16')
            start_field = getattr(field, 'start_field', None)
            end_field = getattr(field, 'end_field', None)
            
            if start_field and end_field:
                start_info = field_info.get(start_field)
                end_info = field_info.get(end_field)
                
                if start_info and end_info:
                     start_byte = start_info['start']
                     # Provide option: End Exclusive or Inclusive?
                     # "End Field" usually implies "Up to end of End Field".
                     end_byte = end_info['start'] + end_info['size']
                     
                     if start_byte < end_byte and end_byte <= len(buffer):
                         data_slice = buffer[start_byte : end_byte]
                         
                         # Calculate Checksum
                         result = checksums.calculate(algo_name, data_slice)
                         
                         # Pack result into buffer at 'offset'
                         # Checksum field has 'struct_format' (e.g. '<H'). Use it.
                         # But Field object doesn't have pack_into helper easily exposed?
                         # PrimitiveField has _struct.
                         if hasattr(field, '_struct'):
                             field._struct.pack_into(buffer, offset, result)
                         else:
                             print(f"Warning: Checksum field {name} is not a PrimitiveField. Cannot pack result.")
            
        return bytes(buffer)

    @classmethod
    def from_bytes(cls, data: bytes) -> Tuple['Message', int]:
        obj = cls()
        offset = 0
        
        for step in cls._packing_plan:
            action, payload = step
            if action == 'struct':
                fmt, field_names, struct_obj = payload
                chunk_size = struct_obj.size
                if offset + chunk_size > len(data):
                    raise ValueError("Not enough data")
                
                chunk = data[offset : offset + chunk_size]
                values = struct_obj.unpack(chunk)
                offset += chunk_size
                
                for name, val in zip(field_names, values):
                    field = cls.fields[name]
                    if hasattr(field, 'enum_cls'):
                        val = field.enum_cls(val) 
                    setattr(obj, name, val)
                    
            elif action == 'complex':
                field_name = payload
                field = cls.fields[field_name]
                
                if field.struct_format:
                    s = struct.Struct(field.struct_format)
                    size = s.size
                    if offset + size > len(data):
                        raise ValueError(f"Not enough data for field {field_name}")
                    
                    if field.__class__ == PrimitiveField or issubclass(field.__class__, PrimitiveField):
                        # Optimization: Struct unpack directly
                        val = s.unpack(data[offset:offset+size])[0]
                    else:
                        # Fixed path but complex (e.g. String Fixed, Array Fixed Primitive)
                        # They implement from_bytes returning (val, size) now
                        val, used = field.from_bytes(data[offset:])
                        # Verify used matches struct size?
                    
                    setattr(obj, field_name, val)
                    offset += size
                
                else:
                    # Dynamic fallback (Array Dynamic, String Variable, etc)
                    # And Fixed Array Complex
                    # field.from_bytes now returns (val, consumed)
                    remaining = data[offset:]
                    val, consumed = field.from_bytes(remaining)
                    setattr(obj, field_name, val)
                    offset += consumed
                    
        return obj, offset

def register(cls_or_none=None, *, system_config_id: str = None):
    """
    Decorator to register a Message class.
    Args:
        system_config_id (str): SPL Tag to associate with this message.
    """
    def wrapper(cls):
        # SPL Filtering at Registration Time?
        # Requirement: "Messages... tagged for inactive configurations must be filtered out at registration (zero runtime cost)."
        # We need to know the 'active' config of the RUNNING process.
        # Ideally, we check a global or env var.
        # For now, let's store the tag/config.
        
        # If system_config_id is a single string or list?
        # Requirement: "A multi-select list assigns these tags to messages." -> List of tags?
        # But decorator param name implies singular 'system_config_id'.
        # Let's support list or string.
        
        # NOTE: In Python backend usage, we might define which configs are active BEFORE importing messages.
        # Registry should have a `set_active_configs([...])` method.
        # But here we are at import time.
        
        # Let's register it with the tag, and let Registry filter at runtime/lookup?
        # "filtered out at registration (zero runtime cost)" -> 
        # Means if I am NOT in Config A, don't even add to _messages.
        
        # For flexibility, we will register it, but maybe Registry has logic.
        
        # Logic: 
        # 1. Harvest fields
        fields = {k: v for k, v in cls.__dict__.items() if isinstance(v, Field)}
        cls.fields = fields
        cls._active_configs = [system_config_id] if system_config_id else []
        
        # 1b. Resolve Hierarchical Endianness
        # Default to Little Endian if not specified or 'Inherit' (Root Default)
        msg_endian = getattr(cls, 'endianness', '<')
        if msg_endian not in ('<', '>'):
            msg_endian = '<'
            
        for f in fields.values():
            f.resolve_endianness(msg_endian)
        
        # 2. Build Packing Plan
        plan = []
        current_fmt = []
        current_names = []
        current_endian = None # None, '<', '>', etc.
        
        def flush():
            if current_fmt:
                # Prepend endianness to the whole chunk
                fmt_str = (current_endian if current_endian else '') + ''.join(current_fmt)
                try:
                    s = struct.Struct(fmt_str)
                    plan.append(('struct', (fmt_str, list(current_names), s)))
                except struct.error as e:
                    # Fallback logging
                    print(f"Error compiling struct: {fmt_str}")
                    raise e
                    
                current_fmt.clear()
                current_names.clear()

        for name, field in fields.items():
            is_primitive = isinstance(field, PrimitiveField)
            is_enum = (field.__class__.__name__ == 'EnumField')
            
            if is_primitive or is_enum:
                # Extract endianness from field.struct_format
                fmt = field.struct_format
                if not fmt: 
                    # Should not happen for primitives
                    continue
                    
                # Check first char
                first = fmt[0]
                if first in '@=<>!':
                    f_endian = first
                    f_char = fmt[1:]
                else:
                    f_endian = '' # Default native? or None? 
                    # If field has no endian char, it uses native.
                    # We treat '' as a distinct endianness 'native'.
                    f_char = fmt
                
                # If endianness changed, flush
                if current_endian is not None and f_endian != current_endian:
                    flush()
                    current_endian = f_endian
                elif current_endian is None:
                    current_endian = f_endian
                
                current_fmt.append(f_char)
                current_names.append(name)
            else:
                flush()
                # Complex field (String, Array, etc) - Reset endian tracking
                current_endian = None 
                plan.append(('complex', name))
        
        flush()
        cls._packing_plan = plan
        
        Registry.register(cls, config_id=system_config_id)
        return cls
        
        Registry.register(cls, config_id=system_config_id)
        return cls

    if cls_or_none is None:
        return wrapper
    return wrapper(cls_or_none)
