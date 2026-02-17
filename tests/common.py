import random
import string
import struct
from enum import IntEnum, Enum
from typing import List

from serializer_core import (
    Message, StringMessage, Field, BitField, Bit,
    EnumField, StringField, FixedPointField, ArrayField,
    UInt8, UInt16, UInt32, UInt64, Int8, Int16, Int32, Int64,
    Float32, Float64, Bool, register
)

# --- Shared Enums ---
class Color(IntEnum):
    RED = 1
    GREEN = 2
    BLUE = 3

class Status(str, Enum):
    OK = "OK"
    ERROR = "ERR"
    WARNING = "WARN"

# --- Binary Kitchen Sink ---

@register
class NestedStruct(Message):
    # Simple nested structure
    id = UInt32()
    value = Float32()

@register
class KitchenSinkBinary(Message):
    endianness = '<' # Default Little
    
    # 1. Primitives & Endianness Override
    magic = UInt16(default=0xCAFE, byte_order='>') # Big Endian
    version = UInt8(default=1)
    
    # 2. All Primitives
    u8_val = UInt8()
    u16_val = UInt16()
    u32_val = UInt32()
    u64_val = UInt64()
    s8_val = Int8()
    s16_val = Int16()
    s32_val = Int32()
    s64_val = Int64()
    f4_val = Float32()
    f8_val = Float64()
    bool_val = Bool()
    
    # 3. BitFields (LSB & MSB)
    # LSB Container
    flags_lsb = BitField([
        Bit(1, 'enable', 'Bool'),
        Bit(3, 'mode', 'UInt32'), 
        Bit(4, 'color', 'Enum', enum_name='Color')
    ], base_type=UInt8, bit_order='LSB') # 1+3+4=8 bits
    
    # MSB Container
    flags_msb = BitField([
        Bit(1, 'valid', 'Bool'),
        Bit(7, 'reserved', 'UInt32')
    ], base_type=UInt8, bit_order='MSB')
    
    # 4. Fixed Point
    # Unsigned Q8.8 (16 bits)
    fp_u = FixedPointField(integer_bits=8, fractional_bits=8, encoding=0)
    # Signed Q7.8 (16 bits) - Encoding 1 (2's complement)
    # 7 int + 8 frac + 1 implicit sign bit in primitive? 
    # Logic: total_bits = int + frac. If encoding=1, uses signed primitive.
    # So 8 int + 8 frac = 16 bits. Can represent -128.0 to 127.99
    fp_s = FixedPointField(integer_bits=7, fractional_bits=8, encoding=1)
    
    # Dir-Mag (Encoding 2). 7 int + 8 frac + 1 explicit sign = 16 bits.
    fp_dm = FixedPointField(integer_bits=7, fractional_bits=8, encoding=2)
    
    # 5. Arrays
    # Fixed Primitive
    scores = ArrayField(item_type=UInt8, count=4, mode='Fixed')
    
    # Dynamic Nested Struct
    # Dynamic Nested Struct (Prefixed)
    # item_count = UInt16() # Removed, Prefixed includes count
    items = ArrayField(item_type=NestedStruct, mode='Prefixed')
    
    # 6. Smart Fields
    # Timestamp (ms requires UInt64)
    ts = UInt64(is_timestamp=True, resolution='ms')
    
    # Length (patches itself) - Start from 'magic', end at 'crc'
    # Note: Backend expects field names. 
    # Let's say it measures everything from magic to before CRC.
    # To test 'Auto-Calculating', we set is_length=True.
    msg_len = UInt16(is_length=True, start_field='magic', end_field='items') 
    
    # Checksum (Footer)
    crc = UInt16(is_checksum=True, algorithm='CRC16', start_field='magic', end_field='msg_len')


# --- String Kitchen Sink ---

@register
class KitchenSinkString(StringMessage):
    protocol_mode = "string"
    
    # Header
    head = StringField(length=4, default="HEAD")
    
    # Delimiters (ID, Type) - handled by StringMessage logic implicitly if fields exist?
    # Or explicitly defined fields?
    # StringProtocol uses 'cmd_type' and 'cmd_str' usually for discrimination?
    # Let's define standard fields.
    
    msg_id = UInt8() # ID
    
    # Required for String Protocol Registry
    cmd_type = StringField(default="TEST", length=4)
    cmd_str = StringField(default="KITCHEN", length=7)
    
    # Body
    label = StringField(length=10, size_mode='Fixed')
    description = StringField(length_field='desc_len', size_mode='Dynamic')
    desc_len = UInt8() # Helper
    
    status = EnumField(enum_cls=Status, storage_type='String') # String Enum
    
    # Checksum
    chk = StringField(length=2, is_checksum=True, algorithm='XOR') # Hex-encoded XOR?


# --- Fuzzing Helpers ---

def fuzz_binary(obj: KitchenSinkBinary):
    obj.u8_val = random.randint(0, 255)
    obj.u16_val = random.randint(0, 65535)
    obj.u32_val = random.randint(0, 2**32-1)
    obj.u64_val = random.randint(0, 2**64-1)
    obj.s8_val = random.randint(-128, 127)
    obj.s16_val = random.randint(-32768, 32767)
    obj.s32_val = random.randint(-2**31, 2**31-1)
    obj.s64_val = random.randint(-2**63, 2**63-1)
    obj.f4_val = random.random() * 1000
    obj.f8_val = random.random() * 100000
    obj.bool_val = random.choice([True, False])
    
    # Bitfields
    # We assign to the container's virtual properties?
    # Currently BitField implementation doesn't automatically create properties on the Message class 
    # unless we mapped them. The Serializer backend `BitField` handles packing.
    # But usually we access `obj.enable`, `obj.mode` if they are registered?
    # Wait, `BitField` class in `fields.py` doesn't magically create attributes on the instance.
    # The `Message` class `__init__` might?
    # Inspecting `Message` code would confirm. 
    # For now, let's assume we set the raw integer if virtuals aren't there, 
    # OR we use the bitfield dict if supported.
    # Actually `BitField` in V2 usually packs fro attributes.
    # Let's try setting attributes.
    # Bitfields
    obj.flags_lsb = {
        'enable': True,
        'mode': 5,
        'color': Color.GREEN
    }
    
    obj.flags_msb = {
        'valid': False,
        'reserved': 12
    }
    # legacy attrs ignored
    # obj.enable = True ...
    
    obj.fp_u = 12.5
    obj.fp_s = -5.55
    obj.fp_dm = -2.5
    
    obj.scores = [random.randint(0, 255) for _ in range(4)]
    
    count = random.randint(0, 5)
    obj.items = []
    for _ in range(count):
        ns = NestedStruct()
        ns.id = random.randint(0, 1000)
        ns.value = random.random()
        obj.items.append(ns)
    
    obj.ts = 0 # Will be auto-set? Or we set it.

def fuzz_string(obj: KitchenSinkString):
    obj.msg_id = random.randint(1, 99)
    obj.label = "TestLabel"
    obj.description = "RandomDesc_" + str(random.randint(0, 100))
    obj.status = random.choice(list(Status))

