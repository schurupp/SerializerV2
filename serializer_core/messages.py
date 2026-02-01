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

    def serialize(self) -> bytes:
        chunks = []
        for step in self._packing_plan:
            action, payload = step
            if action == 'struct':
                fmt, field_names, struct_obj = payload
                values = []
                for name in field_names:
                    val = getattr(self, name)
                    if hasattr(val, 'value'): # Enum
                        val = val.value
                    values.append(val)
                chunks.append(struct_obj.pack(*values))
            elif action == 'complex':
                field_name = payload
                field = self.fields[field_name]
                val = getattr(self, field_name)
                chunks.append(field.to_bytes(val))
        return b''.join(chunks)

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
        
        # 2. Build Packing Plan
        plan = []
        current_fmt = []
        current_names = []
        
        def flush():
            if current_fmt:
                fmt_str = '<' + ''.join(current_fmt)
                s = struct.Struct(fmt_str)
                plan.append(('struct', (fmt_str, list(current_names), s)))
                current_fmt.clear()
                current_names.clear()

        for name, field in fields.items():
            is_primitive = isinstance(field, PrimitiveField)
            is_enum = (field.__class__.__name__ == 'EnumField')
            
            if is_primitive or is_enum:
                current_fmt.append(field.struct_format)
                current_names.append(name)
            else:
                flush()
                # Pass explicit type if needed or just name
                plan.append(('complex', name))
        
        flush()
        cls._packing_plan = plan
        
        Registry.register(cls, config_id=system_config_id)
        return cls

    if cls_or_none is None:
        return wrapper
    return wrapper(cls_or_none)
