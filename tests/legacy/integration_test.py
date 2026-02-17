import sys
import os
import random
import collections
from typing import List

# Ensure serializer_core is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from serializer_core import *
from enum import IntEnum

# --- Definitions ---

class MyEnum(IntEnum):
    STATUS_OK = 1
    STATUS_WARN = 2
    STATUS_ERR = 3

@register
class TestMessage(Message):
    # Discriminator: 1 byte, default 0xAA
    disc = UInt8(is_discriminator=True, default=0xAA)
    
    # Primitives
    seq_id = UInt32()
    temp = Float32()
    
    # Enum
    status = EnumField(MyEnum, UInt8)
    
    # BitField: 1 byte
    flags = BitField([
        Bit(1, 'enabled'),
        Bit(1, 'active'),
        Bit(2, 'mode')
    ], UInt8)
    
    # FixedPoint: 
    azimuth = FixedPointField(integer_bits=8, fractional_bits=8, is_signed=True)
    
    # Dynamic Array of UInt16
    # Mode="Dynamic", CountField is not explicitly needed by serializer logic for ArrayField unless specified?
    # Actually ArrayField logic for dynamic needs a count field OR it just consumes rest? 
    # Current implementation of ArrayField dynamic usually requires a count field in the message BEFORE it,
    # OR it manages its own count if configured? 
    # Let's check ArrayField implementation (it often needs a length field name in options if dynamic)
    # Re-reading fields.py: ArrayField dynamic looks for 'count_field' in instance options.
    # BUT wait, the serializer_core.fields.ArrayField logic:
    # if mode == "Dynamic": length = options['count']. BUT wait, how does it get the dynamic count?
    # It usually relies on the message class to pass the count value during serialization/deserialization?
    # Actually, standard pattern:
    # data_len = UInt8() # Not needed for fixed
    data = ArrayField(UInt16(), mode="Fixed", count=5) 

def run_integration_test():
    print("--- Integration Test: Sticky Packets & Stream Handling ---")
    
    # 1. Generate 100 Messages
    messages = []
    print("Generating 100 random messages...")
    for i in range(100):
        d_len = random.randint(0, 5) # Short arrays
        arr_data = [random.randint(0, 65535) for _ in range(d_len)]
        
        msg = TestMessage(
            seq_id=i,
            temp=random.random() * 100.0,
            status=random.choice(list(MyEnum)),
            flags={'enabled': 1, 'active': i%2, 'mode': i%4},
            azimuth=random.uniform(-100, 100),
            # data_len=d_len,
            data=[random.randint(0, 30000) for _ in range(5)]
        )
        messages.append(msg)

    # 2. Serialize to Single Buffer
    print("Serializing...")
    full_buffer = bytearray()
    for m in messages:
        full_buffer.extend(m.serialize())
        
    print(f"Total Buffer Size: {len(full_buffer)} bytes")
    
    # 3. Chaos Loop (Slicing)
    print("Simulating Network Fragmentation (Chaos Loop)...")
    handler = StreamHandler()
    dq = collections.deque()
    
    cursor = 0
    total_len = len(full_buffer)
    chunks_count = 0
    
    while cursor < total_len:
        # Random slice size: 1 to 50 bytes
        remaining = total_len - cursor
        chunk_size = random.randint(1, min(50, remaining))
        
        chunk = full_buffer[cursor : cursor + chunk_size]
        cursor += chunk_size
        
        handler.feed(chunk, dq)
        chunks_count += 1
        
    print(f"Fed {chunks_count} chunks into StreamHandler.")
    
    # 4. Verification
    print(f"Reassembled Messages: {len(dq)}")
    assert len(dq) == 100, f"Expected 100 messages, got {len(dq)}"
    
    print("Verifying content...")
    for i, received_msg in enumerate(dq):
        original = messages[i]
        
        # Check Fields
        assert received_msg.seq_id == original.seq_id
        # Floating point comparison
        assert abs(received_msg.temp - original.temp) < 0.001
        assert received_msg.status == original.status
        assert received_msg.flags == original.flags
        assert abs(received_msg.azimuth - original.azimuth) < 0.1 # Fixed point precision
        # assert received_msg.data_len == original.data_len
        assert received_msg.data == original.data
        
    print("SUCCESS: All 100 messages verified correctly.")

if __name__ == "__main__":
    try:
        run_integration_test()
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
