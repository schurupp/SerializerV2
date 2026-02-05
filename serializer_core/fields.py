
import struct
from abc import ABC, abstractmethod
from typing import Any, Optional, Union, Tuple, List, Type
from enum import IntEnum
import time

class Field(ABC):
    """
    Base class for all serialization fields.
    Refined V2: No min/max validation. Added is_checksum.
    """
    def __init__(
        self,
        default: Any = None,
        is_discriminator: bool = False,
        is_checksum: bool = False,
        is_length: bool = False,
        is_timestamp: bool = False,
        byte_order: Optional[str] = None, # None=Inherit, < Little, > Big
        **kwargs
    ):
        self.default = default
        self.is_discriminator = is_discriminator
        self.is_checksum = is_checksum
        self.is_length = is_length
        self.is_timestamp = is_timestamp
        self.byte_order = byte_order
        
        # Store arbitrary metadata (algorithm, start_field, etc.)
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.struct_format: str = "" 

    def validate(self, value: Any) -> Any:
        return value

    def resolve_endianness(self, default_endian: str):
        """Called by Message during registration if byte_order is Inherit."""
        if self.byte_order is None:
            self.byte_order = default_endian
            self._on_endian_resolved()

    def _on_endian_resolved(self):
        """Hook for subclasses to rebuild structs."""
        pass

    @abstractmethod
    def to_bytes(self, value: Any) -> bytes:
        pass

    def to_string(self, value: Any) -> str:
        """Serialize to string (for String Protocol)."""
        if value is None and self.default is not None:
            value = self.default
        if value is None: return ""
        return str(value)

    @abstractmethod
    def from_bytes(self, data: bytes) -> Tuple[Any, int]:
        """Returns (value, consumed_bytes)"""
        pass

class PrimitiveField(Field):
    def __init__(self, fmt_char: str, **kwargs):
        super().__init__(**kwargs)
        self.fmt_char = fmt_char
        self.resolution = kwargs.get('resolution', 's') # s or ms
        # Construct format with endianness
        if self.byte_order:
            self.struct_format = f"{self.byte_order}{fmt_char}"
            self._struct = struct.Struct(self.struct_format)
        else:
            self.struct_format = ""
            self._struct = None

    def _on_endian_resolved(self):
        if self.byte_order:
            self.struct_format = f"{self.byte_order}{self.fmt_char}"
            self._struct = struct.Struct(self.struct_format)

    def to_bytes(self, value: Any) -> bytes:
        if self.is_timestamp:
            # Inject current time
            t = time.time()
            if self.resolution == 'ms':
                t *= 1000
            value = int(t)
            
        if value is None and self.default is not None:
             value = self.default
        if value is None:
             value = 0
        return self._struct.pack(value)

    def from_bytes(self, data: bytes) -> Tuple[Any, int]:
        size = self._struct.size
        if len(data) < size:
             raise ValueError(f"Not enough data for {self.__class__.__name__}")
        val = self._struct.unpack(data[:size])[0]
        return val, size

# Concrete Primitives
class UInt8(PrimitiveField):
    def __init__(self, **kwargs): super().__init__('B', **kwargs)
class Int8(PrimitiveField):
    def __init__(self, **kwargs): super().__init__('b', **kwargs)
class UInt16(PrimitiveField):
    def __init__(self, **kwargs): super().__init__('H', **kwargs)
class Int16(PrimitiveField):
    def __init__(self, **kwargs): super().__init__('h', **kwargs)
class UInt32(PrimitiveField):
    def __init__(self, **kwargs): super().__init__('I', **kwargs)
class Int32(PrimitiveField):
    def __init__(self, **kwargs): super().__init__('i', **kwargs)
class UInt64(PrimitiveField):
    def __init__(self, **kwargs): super().__init__('Q', **kwargs)
class Int64(PrimitiveField):
    def __init__(self, **kwargs): super().__init__('q', **kwargs)
class Float32(PrimitiveField):
    def __init__(self, **kwargs): super().__init__('f', **kwargs)
class Float64(PrimitiveField):
    def __init__(self, **kwargs): super().__init__('d', **kwargs)
class Bool(PrimitiveField):
    def __init__(self, **kwargs): super().__init__('?', **kwargs)

# Advanced Fields

class StringField(Field):
    def __init__(self, size_mode: str = "Fixed", length: int = 0, encoding: str = "utf-8", **kwargs):
        super().__init__(**kwargs)
        self.size_mode = size_mode
        self.length = length
        self.encoding = encoding
        
        if self.size_mode == "Fixed":
            self.struct_format = f"{length}s"
            self._struct = struct.Struct(self.struct_format)

    def to_bytes(self, value: str) -> bytes:
        if value is None and self.default is not None:
             value = self.default
        if value is None: value = ""
        
        encoded = value.encode(self.encoding)
        if self.size_mode == "Fixed":
            if len(encoded) > self.length:
                encoded = encoded[:self.length]
            return self._struct.pack(encoded)
        else:
            l = len(encoded)
            return struct.pack('<I', l) + encoded

    def from_bytes(self, data: bytes) -> Tuple[str, int]:
        if self.size_mode == "Fixed":
            size = self._struct.size
            if len(data) < size: raise ValueError("Not enough data")
            raw = self._struct.unpack(data[:size])[0]
            val = raw.decode(self.encoding).rstrip('\x00')
            return val, size
        else:
            if len(data) < 4:
                raise ValueError("Not enough data for String length")
            l = struct.unpack('<I', data[:4])[0]
            total_len = 4 + l
            if len(data) < total_len:
                raise ValueError("Not enough data for String content")
            
            val_bytes = data[4:total_len]
            if isinstance(val_bytes, memoryview):
                val_bytes = bytes(val_bytes)
            return val_bytes.decode(self.encoding), total_len

class EnumField(Field):
    def __init__(self, enum_cls: Type[IntEnum], storage_type: str = "UInt8", **kwargs):
        super().__init__(**kwargs)
        self.enum_cls = enum_cls
        self.storage_type = storage_type
        
        type_map = {
            "UInt8": UInt8, "Int8": Int8,
            "UInt16": UInt16, "Int16": Int16,
            "UInt32": UInt32, "Int32": Int32,
            "String": StringField 
        }
        if storage_type == "String":
             base_cls = StringField
        else:
             base_cls = type_map.get(storage_type, UInt8)
             
        self.base_field = base_cls(**kwargs)
        self.struct_format = getattr(self.base_field, 'struct_format', None)
        self._struct = getattr(self.base_field, '_struct', None)

    def _on_endian_resolved(self):
        self.base_field.resolve_endianness(self.byte_order)
        self.struct_format = getattr(self.base_field, 'struct_format', None)
        self._struct = getattr(self.base_field, '_struct', None)

    def to_bytes(self, value: Any) -> bytes:
        if value is None and self.default is not None:
            value = self.default
            
        if isinstance(value, self.enum_cls):
            val_to_pack = value.value
        else:
            val_to_pack = value
        return self.base_field.to_bytes(val_to_pack)

    def to_string(self, value: Any) -> str:
        if value is None and self.default is not None:
            value = self.default
        if value is None: return ""
        
        if isinstance(value, self.enum_cls):
            return value.name
        
        try:
            member = self.enum_cls(value)
            return member.name
        except (ValueError, TypeError):
            return str(value)

    def from_bytes(self, data: bytes) -> Tuple[Any, int]:
        val, size = self.base_field.from_bytes(data)
        try:
            return self.enum_cls(val), size
        except ValueError:
            return val, size

class FixedPointField(Field):
    def __init__(self, integer_bits: int, fractional_bits: int, encoding: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.integer_bits = integer_bits
        self.fractional_bits = fractional_bits
        self.encoding = encoding # 0, 1, 2
        
        msg_extra_bit = 1 if encoding == 2 else 0
        self.total_bits = integer_bits + fractional_bits + msg_extra_bit
        self.scale = 1 << fractional_bits
        
        if self.byte_order:
             self._create_struct()
        else:
             self.struct_format = ""
             self._struct = None

    def _on_endian_resolved(self):
        self._create_struct()

    def _create_struct(self):
        if self.total_bits <= 8:
            fmt = 'b' if self.encoding == 1 else 'B'
        elif self.total_bits <= 16:
            fmt = 'h' if self.encoding == 1 else 'H'
        elif self.total_bits <= 32:
            fmt = 'i' if self.encoding == 1 else 'I'
        elif self.total_bits <= 64:
            fmt = 'q' if self.encoding == 1 else 'Q'
        else:
            raise ValueError("Too many bits for standard primitive backing")
            
        self.struct_format = f"{self.byte_order}{fmt}"
        self._struct = struct.Struct(self.struct_format)

    def to_bytes(self, value: float) -> bytes:
        if value is None and self.default is not None:
             value = self.default
        if value is None: value = 0.0

        if self.encoding == 2: # Dir-Mag
            direction_flag = 1 if value < 0 else 0
            magnitude = abs(value)
            raw_val = int(magnitude * self.scale)
            mask = (1 << (self.integer_bits + self.fractional_bits)) - 1
            raw_val &= mask
            msb_pos = self.integer_bits + self.fractional_bits
            final_val = raw_val | (direction_flag << msb_pos)
            return self._struct.pack(final_val)
        else:
            raw_val = int(value * self.scale)
            return self._struct.pack(raw_val)

    def from_bytes(self, data: bytes) -> Tuple[float, int]:
        size = self._struct.size
        raw_val = self._struct.unpack(data[:size])[0]
        
        if self.encoding == 2: # Dir-Mag
            msb_pos = self.integer_bits + self.fractional_bits
            direction_flag = (raw_val >> msb_pos) & 1
            mask = (1 << msb_pos) - 1
            magnitude_raw = raw_val & mask
            val = magnitude_raw / self.scale
            return (-val if direction_flag else val), size
        else:
            return (raw_val / self.scale), size

class Bit:
    def __init__(self, width: int, name: str, data_type: str = "UInt", default_value: int = 0, enum_name: str = None):
        self.width = width
        self.name = name
        self.data_type = data_type
        self.default_value = default_value
        self.enum_name = enum_name

class BitField(Field):
    def __init__(self, bits: List[Bit], base_type: Type[PrimitiveField] = UInt32, bit_order: str = "LSB", **kwargs):
        super().__init__(**kwargs)
        self.bits = bits
        self.bit_order = bit_order
        self.base_field = base_type(**kwargs)
        self.struct_format = self.base_field.struct_format
        
    def _on_endian_resolved(self):
        self.base_field.resolve_endianness(self.byte_order)
        self.struct_format = self.base_field.struct_format
        
    def to_bytes(self, value: Union[dict, int]) -> bytes:
        if value is None and self.default is not None:
             value = self.default
        if value is None: value = 0
             
        if isinstance(value, int):
            packed_int = value
        else:
            packed_int = 0
            total_width = sum(b.width for b in self.bits)
            current_shift = 0
            
            for b in self.bits:
                val = value.get(b.name, 0)
                mask = (1 << b.width) - 1
                val &= mask
                
                if self.bit_order == "MSB":
                     shift = total_width - current_shift - b.width
                     packed_int |= (val << shift)
                else:
                     packed_int |= (val << current_shift)
                     
                current_shift += b.width
                
        return self.base_field.to_bytes(packed_int)

    def from_bytes(self, data: bytes) -> Tuple[dict, int]:
        raw_val, size = self.base_field.from_bytes(data)
        result = {}
        total_width = sum(b.width for b in self.bits)
        current_shift = 0
        
        for b in self.bits:
            mask = (1 << b.width) - 1
            
            if self.bit_order == "MSB":
                shift = total_width - current_shift - b.width
                val = (raw_val >> shift) & mask
            else:
                val = (raw_val >> current_shift) & mask
                
            result[b.name] = val
            current_shift += b.width
        return result, size

class ArrayField(Field):
    def __init__(self, item_type: Union[Field, Type[Field]], mode: str = "Fixed", count: int = 0, count_field: str = None, **kwargs):
        super().__init__(**kwargs)
        
        if isinstance(item_type, type) and issubclass(item_type, Field):
            item_type = item_type()
            
        self.item_type = item_type
        self.mode = mode
        self.count = count 
        self.count_field = count_field 
        
        if mode == "Fixed" and isinstance(item_type, PrimitiveField):
             try:
                 fmt_char = item_type.fmt_char
                 bo = item_type.byte_order
                 self.struct_format = f"{bo}{count}{fmt_char}"
             except AttributeError:
                 self.struct_format = ""

    def _on_endian_resolved(self):
        if isinstance(self.item_type, Field):
             self.item_type.resolve_endianness(self.byte_order)
             
        if self.mode == "Fixed" and isinstance(self.item_type, PrimitiveField):
             try:
                 fmt_char = self.item_type.fmt_char
                 bo = self.item_type.byte_order
                 if bo is None: bo = ""
                 self.struct_format = f"{bo}{self.count}{fmt_char}"
             except AttributeError:
                 self.struct_format = ""

    def to_bytes(self, value: list) -> bytes:
        if value is None and self.default is not None:
             value = self.default
        if value is None: value = []

        if self.mode == "Fixed":
            current_len = len(value)
            if current_len < self.count:
                value.extend([None] * (self.count - current_len))
            elif current_len > self.count:
                value = value[:self.count]
            
            if self.struct_format:
                 sanitized = [(v if v is not None else 0) for v in value]
                 return struct.pack(self.struct_format, *sanitized)
            else:
                 return self._serialize_items(value)
        elif self.mode == "Prefixed":
             # Prefix with Count (UInt32 Little Endian Default)
             prefix = struct.pack('<I', len(value))
             return prefix + self._serialize_items(value)
        else:
             return self._serialize_items(value)

    def _serialize_items(self, value):
        from .messages import Message
        chunks = []
        for v in value:
            if hasattr(self.item_type, 'to_bytes'):
                chunks.append(self.item_type.to_bytes(v))
            elif isinstance(self.item_type, type) and issubclass(self.item_type, Message):
                chunks.append(v.serialize())
            else:
                if hasattr(v, 'serialize'):
                    chunks.append(v.serialize())
                else:
                    raise TypeError(f"Cannot serialize array item {v} with type {self.item_type}")
        return b''.join(chunks)

    def from_bytes(self, data: bytes) -> Tuple[list, int]:
        values = []
        
        if self.mode == "Fixed":
            if self.struct_format:
                 s = struct.Struct(self.struct_format)
                 size = s.size
                 if len(data) < size: raise ValueError("Not enough data for Array")
                 return list(s.unpack(data[:size])), size
            else:
                 offset = 0
                 for _ in range(self.count):
                     val, cons = self.item_type.from_bytes(data[offset:])
                     values.append(val)
                     offset += cons
                 return values, offset
                 
        elif self.mode == "Dynamic":
            # Consume remaining
            offset = 0
            while offset < len(data):
                try:
                    val, cons = self.item_type.from_bytes(data[offset:])
                    values.append(val)
                    offset += cons
                except (ValueError, struct.error):
                    break
            return values, offset
        elif self.mode == "Prefixed":
            if len(data) < 4: raise ValueError("Not enough data for Array Prefix")
            count = struct.unpack('<I', data[:4])[0]
            offset = 4
            for _ in range(count):
                 val, cons = self.item_type.from_bytes(data[offset:])
                 values.append(val)
                 offset += cons
            return values, offset
            
        return [], 0
