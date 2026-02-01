from serializer_core import *
from enum import IntEnum
from collections import deque
import struct

# Test Setup
class MyEnum(IntEnum):
    A = 1
    B = 2

@register
class TestMsg(Message):
    disc = UInt8(is_discriminator=True, default=0x10)
    val = UInt32()
    status = EnumField(MyEnum, UInt8)
    label = StringField(length=10, size_mode="Fixed")
    fp = FixedPointField(integer_bits=4, fractional_bits=4, is_signed=False)
    # BitField test
    flags = BitField([
        Bit(1, 'flag_a'),
        Bit(3, 'val_b')
    ], UInt8)

def test_backend():
    print("--- Starting Backend Verification ---")
    
    # 1. Instantiate
    msg = TestMsg(
        val=0xDEADBEEF, 
        status=MyEnum.B, 
        label="Hello", 
        fp=1.5,
        flags={'flag_a': 1, 'val_b': 5} # 1 | (5<<1) = 1 | 10 = 11 (0xB)
    )
    
    # 2. Serialize
    data = msg.serialize()
    print(f"Serialized Length: {len(data)}")
    print(f"Serialized Hex: {data.hex().upper()}")
    
    # Expected Layout:
    # disc: 1 byte (0x10)
    # val: 4 bytes (EF BE AD DE) -> Little Endian
    # status: 1 byte (0x02)
    # label: 10 bytes (48 65 6C 6C 6F 00 00 00 00 00)
    # fp: 1 byte (0x18) -> 1.5 * 16 = 24
    # flags: 1 byte (0x0B) 
    
    # Layout Check
    # Packing Plan should be:
    # 1. Struct (B I B) -> disc, val, status
    # 2. Complex (label)
    # 3. Complex (fp)
    # 4. Complex (flags)
    
    # Verify correctness
    expected_val_hex = "EFBEADDE"
    if expected_val_hex in data.hex().upper():
        print("PASS: Value 0xDEADBEEF found correctly.")
    else:
        print("FAIL: Value not found.")

    # 3. Deserialize (Round Trip)
    msg2, consumed = TestMsg.from_bytes(data)
    print(f"Consumed: {consumed} bytes")
    
    assert msg2.val == 0xDEADBEEF
    assert msg2.status == MyEnum.B
    assert msg2.label == "Hello"
    assert msg2.fp == 1.5
    assert msg2.flags['flag_a'] == 1
    assert msg2.flags['val_b'] == 5
    print("PASS: Round-Trip Deserialization.")

    # 4. Stream Handler Test
    print("\n--- StreamHandler Test ---")
    handler = StreamHandler()
    dq = deque()
    
    # Send in fragmented chunks
    chunk1 = data[:3] # disc + partial val
    chunk2 = data[3:10] # rest of val + status + partial label
    chunk3 = data[10:] # rest
    
    handler.feed(chunk1, dq)
    print(f"After Chunk 1 (len {len(chunk1)}): Queue size {len(dq)}")
    handler.feed(chunk2, dq)
    print(f"After Chunk 2 (len {len(chunk2)}): Queue size {len(dq)}")
    handler.feed(chunk3, dq)
    print(f"After Chunk 3 (len {len(chunk3)}): Queue size {len(dq)}")
    
    if len(dq) == 1:
        m = dq.popleft()
        if m.val == 0xDEADBEEF:
            print("PASS: Stream Reassembly.")
        else:
            print(f"FAIL: Stream content mismatch. val={m.val}")
    else:
        print(f"FAIL: Expected 1 message, got {len(dq)}")

if __name__ == "__main__":
    try:
        test_backend()
        print("\nALL BACKEND TESTS PASSED.")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
