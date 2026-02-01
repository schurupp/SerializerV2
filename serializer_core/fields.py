import struct
from abc import ABC, abstractmethod
from typing import Any, Optional, Union, Tuple, List, Type
from enum import IntEnum

class Field(ABC):
    """
    Base class for all serialization fields.
    Refined V2: No min/max validation. Added is_checksum.
    """
    def __init__(
        self,
        default: Any = None,
        is_discriminator: bool = False,
        is_checksum: bool = False, # NEW
        is_timestamp: bool = False,
    ):
        self.default = default
        self.is_discriminator = is_discriminator
        self.is_checksum = is_checksum
        self.is_timestamp = is_timestamp
        self.struct_format: str = "" 

    def validate(self, value: Any) -> Any:
        # Refinement: No more min/max validation
        return value

    @abstractmethod
    def to_bytes(self, value: Any) -> bytes:
        pass

    @abstractmethod
    def from_bytes(self, data: bytes) -> Tuple[Any, int]:
        """Returns (value, consumed_bytes)"""
        pass

class PrimitiveField(Field):
    def __init__(self, fmt: str, **kwargs):
        super().__init__(**kwargs)
        self.struct_format = fmt
        self._struct = struct.Struct(fmt)

    def to_bytes(self, value: Any) -> bytes:
        # If None, use default? Message handles this usually, 
        # but to_bytes is called with a value.
        # If value is None here, it might crash pack.
        if value is None and self.default is not None:
             value = self.default
        return self._struct.pack(value)

    def from_bytes(self, data: bytes) -> Tuple[Any, int]:
        # Primitive fields always consume their struct size
        # We might be passed more data than needed in dynamic context,
        # so we rely on struct unpack to take what it needs?
        # struct.unpack expects exact size usually? 
        # No, unpack requires buffer to be *at least* size.
        # But unpack returns tuple.
        # We should slice locally to be safe or trust unpack?
        # Safe: slice.
        size = self._struct.size
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
        
        # If default is also None and value None? Crash or empty string?
        if value is None: value = ""
        
        encoded = value.encode(self.encoding)
        if self.size_mode == "Fixed":
            if len(encoded) > self.length:
                encoded = encoded[:self.length]
            return self._struct.pack(encoded)
        else:
            l = len(encoded)
            return struct.pack('I', l) + encoded

    def from_bytes(self, data: bytes) -> Tuple[str, int]:
        if self.size_mode == "Fixed":
            raw = self._struct.unpack(data[:self._struct.size])[0]
            val = raw.decode(self.encoding).rstrip('\x00')
            return val, self._struct.size
        else:
            # Variable length: Read 4 byte length prefix first
            if len(data) < 4:
                raise ValueError("Not enough data for String length")
            l = struct.unpack('I', data[:4])[0]
            total_len = 4 + l
            if len(data) < total_len:
                raise ValueError("Not enough data for String content")
            
            val_bytes = data[4:total_len]
            return val_bytes.decode(self.encoding), total_len

class EnumField(Field):
    def __init__(self, enum_cls: Type[IntEnum], base_type: Type[PrimitiveField] = UInt8, **kwargs):
        super().__init__(**kwargs)
        self.enum_cls = enum_cls
        self.base_field = base_type(**kwargs)
        self.struct_format = self.base_field.struct_format

    def to_bytes(self, value: Any) -> bytes:
        if value is None and self.default is not None:
            value = self.default
            
        if isinstance(value, self.enum_cls):
            val_to_pack = value.value
        else:
            val_to_pack = value
        return self.base_field.to_bytes(val_to_pack)

    def from_bytes(self, data: bytes) -> Tuple[Any, int]:
        val, size = self.base_field.from_bytes(data)
        try:
            return self.enum_cls(val), size
        except ValueError:
            return val, size

class FixedPointField(Field):
    def __init__(self, integer_bits: int, fractional_bits: int, encoding: int = 0, **kwargs):
        """
        encoding: 0=Unsigned, 1=Signed, 2=Direction-Magnitude
        """
        super().__init__(**kwargs)
        self.integer_bits = integer_bits
        self.fractional_bits = fractional_bits
        self.encoding = encoding # 0, 1, 2
        
        # Determine total bits
        msg_extra_bit = 1 if encoding == 2 else 0
        self.total_bits = integer_bits + fractional_bits + msg_extra_bit
        self.scale = 1 << fractional_bits
        
        # Backing Primitive
        if self.total_bits <= 8:
            # Signed if mode 1, else Unsigned (DirMag is unsigned int with MSB interpretation logic)
            self.fmt = 'b' if encoding == 1 else 'B'
        elif self.total_bits <= 16:
            self.fmt = 'h' if encoding == 1 else 'H'
        elif self.total_bits <= 32:
            self.fmt = 'i' if encoding == 1 else 'I'
        elif self.total_bits <= 64:
            self.fmt = 'q' if encoding == 1 else 'Q'
        else:
            raise ValueError("Too many bits for standard primitive backing")
            
        self._struct = struct.Struct(self.fmt)
        self.struct_format = self.fmt

    def to_bytes(self, value: float) -> bytes:
        if value is None and self.default is not None:
             value = self.default
        if value is None: value = 0.0

        if self.encoding == 2: # Dir-Mag
            direction_flag = 1 if value < 0 else 0
            magnitude = abs(value)
            raw_val = int(magnitude * self.scale)
            # Mask magnitude
            mask = (1 << (self.integer_bits + self.fractional_bits)) - 1
            raw_val &= mask
            # Add MSB
            msb_pos = self.integer_bits + self.fractional_bits
            final_val = raw_val | (direction_flag << msb_pos)
            return self._struct.pack(final_val)
        else:
            # Normal scaling
            raw_val = int(value * self.scale)
            # Struct pack handles 2's complement for signed, or bounds for unsigned
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
    def __init__(self, bits: List[Bit], base_type: Type[PrimitiveField] = UInt32, **kwargs):
        super().__init__(**kwargs)
        self.bits = bits
        self.base_field = base_type(**kwargs)
        self.struct_format = self.base_field.struct_format
        
    def to_bytes(self, value: dict) -> bytes:
        if value is None and self.default is not None:
             value = self.default
        if value is None: value = {}
             
        packed_int = 0
        current_shift = 0
        for b in self.bits:
            val = value.get(b.name, 0)
            mask = (1 << b.width) - 1
            val &= mask
            packed_int |= (val << current_shift)
            current_shift += b.width
        return self.base_field.to_bytes(packed_int)

    def from_bytes(self, data: bytes) -> Tuple[dict, int]:
        raw_val, size = self.base_field.from_bytes(data)
        result = {}
        current_shift = 0
        for b in self.bits:
            mask = (1 << b.width) - 1
            val = (raw_val >> current_shift) & mask
            result[b.name] = val
            current_shift += b.width
        return result, size

class ArrayField(Field):
    def __init__(self, item_type: Field, mode: str = "Fixed", count: int = 0, count_field: str = None, **kwargs):
        super().__init__(**kwargs)
        self.item_type = item_type
        self.mode = mode
        self.count = count 
        self.count_field = count_field 
        
        if mode == "Fixed" and isinstance(item_type, PrimitiveField):
             self.struct_format = f"{count}{item_type.struct_format}"

    def to_bytes(self, value: list) -> bytes:
        if value is None and self.default is not None:
             value = self.default
        if value is None: value = []

        if self.mode == "Fixed":
            if len(value) != self.count:
                # pad or truncate? Requirements strict? 
                # Let's just user helper.
                pass
            if self.struct_format:
                 return struct.pack(self.struct_format, *value)
            else:
                 return b''.join(self.item_type.to_bytes(v) for v in value)
        else:
             return b''.join(self.item_type.to_bytes(v) for v in value)

    def from_bytes(self, data: bytes) -> Tuple[list, int]:
        values = []
        total_consumed = 0
        
        if self.mode == "Fixed":
            # If primitive packed
            if self.struct_format:
                 count = self.count
                 # struct format is e.g. "5I"
                 # struct.calcsize can tell us bytes
                 s = struct.Struct(self.struct_format)
                 size = s.size
                 return list(s.unpack(data[:size])), size
            else:
                 # Fixed count, complex items
                 offset = 0
                 for _ in range(self.count):
                     val, cons = self.item_type.from_bytes(data[offset:])
                     values.append(val)
                     offset += cons
                 return values, offset
                 
        elif self.mode == "Dynamic":
            # Dynamic means we read until end of stream?
            # OR we expect a length prefix?
            # Standard pattern for Dynamic Array in this framework (from to_bytes):
            # It blindly joins bytes.
            # If 'count_field' exists, Message usually handles it?
            # No, if Field is responsible for deserializing itself:
            # If no length prefix in stream, we can only read until EOF?
            # But we might be in middle of message.
            
            # Assumption: Dynamic Arrays in this V2 framework 
            # are usually "Rest of Message" OR implicitly length-prefixed if we enforce it.
            # BUT `to_bytes` didn't enforce length prefix.
            # So `from_bytes` consumes ALL remaining data?
            
            # Let's assume consumes all remaining for now (Tier 3 usage).
            # To be robust, one should use Fixed array or have a length prefix logic.
            # If we want to support count_field, we need access to the message context (fields dict values), 
            # which we don't have here easily.
            
            # For Tier 3, `targets` is dynamic.
            offset = 0
            while offset < len(data):
                try:
                    val, cons = self.item_type.from_bytes(data[offset:])
                    values.append(val)
                    offset += cons
                except (ValueError, struct.error):
                    # Stop if not enough data for next item
                    break
            return values, offset
            
        return [], 0
