import sys
import os
import time
import struct
import random
from enum import IntEnum

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from serializer_core import *

# --- Definitions ---

# Tier 2 Helper
class StatusEnum(IntEnum):
    IDLE = 0
    ACTIVE = 1
    ERROR = 2
    # 3 bits max = 7
    UNKNOWN = 7

# Tier 3 Helper
class MetaEnum(IntEnum):
    A = 1
    B = 2
    C = 3

class TargetStructField(Field):
    """Custom field for Tier 3 'TargetStruct': ID (UInt32) + Range (Float32)"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.struct_format = '<If' # 8 bytes
        self._struct = struct.Struct(self.struct_format)

    def to_bytes(self, value):
        # value is dict {'id': int, 'rng': float}
        return self._struct.pack(value.get('id',0), value.get('rng',0.0))

    def from_bytes(self, data):
        i, r = self._struct.unpack(data)
        return {'id': i, 'rng': r}

# --- Message Classes ---

# Tier 1: The Speedster
@register
class Tier1Msg(Message):
    msg_id = UInt32(is_discriminator=True, default=0x11)
    timestamp = Float64()
    status = UInt8()
    value_a = Float32()
    value_b = Float32()

# Tier 2: The Standard Payload
@register
class Tier2Msg(Message):
    msg_id = UInt32(is_discriminator=True, default=0x22)
    
    # 1 Bool, 1 Enum(3-bit), 1 UInt(4-bit) = 1+3+4 = 8 bits = UInt8
    flags = BitField([
        Bit(1, 'flag_bool'),
        Bit(3, 'flag_enum'),
        Bit(4, 'flag_uint')
    ], UInt8)
    
    # 12 int + 4 frac + 1 direction = 17 bits -> Fits in 32-bit (UInt32/Int32 backing)
    # is_signed=True for direction support mechanism in FixedPointField?
    # FixedPointField logic: if has_direction, adds MSB.
    azimuth = FixedPointField(integer_bits=12, fractional_bits=4, has_direction=True)
    
    label = StringField(size_mode="Fixed", length=8)
    checksum = UInt16(is_checksum=True)

# Tier 3: The Heavyweight
@register
class Tier3Msg(Message):
    msg_id = UInt32(is_discriminator=True, default=0x33)
    target_count = UInt8()
    
    # Dynamic Array of custom structs
    # We simulate "linked to target_count" by just providing the array data.
    # The 'target_count' field is just a regular field here, unless we implement specific linking logic.
    # But usually serialization fills the count automatically or we set it manually.
    # We'll set it manually for correctness validation if needed.
    targets = ArrayField(TargetStructField(), mode="Dynamic", count_field="target_count")
    
    description = StringField(size_mode="Variable")
    
    # Fixed Array of Enums
    metadata = ArrayField(EnumField(MetaEnum, UInt8), mode="Fixed", count=5)


# --- Benchmark Logic ---

def run_benchmark():
    ITERATIONS = 500_000
    print(f"--- Complexity Benchmark: {ITERATIONS} iterations per Tier ---")
    print(f"{'Complexity Level':<20} | {'Ser Speed (msgs/sec)':<22} | {'Deser Speed (msgs/sec)':<24} | {'Msg Size (avg)':<15}")
    print("-" * 90)

    tiers = [
        ("Tier 1 (Speedster)", Tier1Msg, generate_tier1),
        ("Tier 2 (Standard)",  Tier2Msg, generate_tier2),
        ("Tier 3 (Heavyweight)", Tier3Msg, generate_tier3)
    ]

    for name, cls, gen_func in tiers:
        # 1. Pre-generate
        # print(f"Generating {name}...")
        payloads = [gen_func(i) for i in range(ITERATIONS)]
        
        # 2. Serialize
        t0 = time.perf_counter()
        
        # We want to measure .serialize() cost. 
        # Using a list comprehension or loop overhead is negligible compared to complex serialization?
        # Let's use a flat loop to be fair and realistic.
        buffer_list = []
        try:
            for p in payloads:
                buffer_list.append(p.serialize())
        except Exception as e:
            print(f"Crash in {name} serialize: {e}")
            import traceback
            traceback.print_exc()
            continue
            
        t1 = time.perf_counter()
        ser_time = t1 - t0
        ser_speed = ITERATIONS / ser_time
        
        # Calculate Avg Size
        total_size = sum(len(b) for b in buffer_list)
        avg_size = total_size / ITERATIONS
        
        # 3. Deserialize
        # We have a list of bytes 'buffer_list'.
        # We verify Registry.deserialize (or class.from_bytes if we want just that speed)
        # Using Registry.deserialize simulates full pipeline (lookup + extract).
        
        # Flatten buffer for stream simulation? 
        # Or distinct calls? 
        # "Measure total time to Registry.deserialize() them back".
        # If we just loop over the list, we measure overhead of loop + deserialize.
        
        t2 = time.perf_counter()
        for b in buffer_list:
            # We must use Registry to test lookup cost too?
            # Or cls.from_bytes?
            # "Registry.deserialize()" requested.
            # Registry needs bytes or memoryview.
            Registry.deserialize(b)
        t3 = time.perf_counter()
        
        deser_time = t3 - t2
        deser_speed = ITERATIONS / deser_time
        
        print(f"{name:<20} | {ser_speed:,.0f}{'':<14} | {deser_speed:,.0f}{'':<16} | {avg_size:.1f} bytes")

def generate_tier1(i):
    return Tier1Msg(
        timestamp=time.time(), 
        status=i%255, 
        value_a=random.random(), 
        value_b=random.random()
    )

def generate_tier2(i):
    return Tier2Msg(
        flags={'flag_bool': i%2, 'flag_enum': (i%7), 'flag_uint': (i%15)},
        azimuth=random.uniform(-180, 180),
        label=f"MSG_{i%99:04d}", # Fixed 8 chars? "MSG_0001" is 8.
        checksum=0 # dummy
    )

def generate_tier3(i):
    # Random target count 1-5
    c = random.randint(1, 4)
    t_list = [{'id': x, 'rng': random.random()} for x in range(c)]
    
    desc = f"Desc {i} - " + ("X" * (i%10))
    
    return Tier3Msg(
        target_count=c, # Explicitly help the field? Or does it update? 
                        # Our current ArrayField "count_field" logic doesn't auto-update the sibling field on serialize
                        # unless we build that. We'll set it manually to be safe.
        targets=t_list,
        description=desc,
        metadata=[MetaEnum.A, MetaEnum.B, MetaEnum.C, MetaEnum.A, MetaEnum.A]
    )

if __name__ == "__main__":
    run_benchmark()
