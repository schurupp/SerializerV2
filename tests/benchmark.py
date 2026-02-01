import sys
import os
import time
import collections

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from serializer_core import *

@register
class BenchMsg(Message):
    # Standard telemetry packet mix
    timestamp = UInt64()
    val1 = Float32()
    val2 = Float32()
    status = UInt8()
    flags = UInt16()

def run_benchmark():
    COUNT = 1_000_000
    print(f"--- Benchmark: {COUNT} messages ---")
    
    # 1. Pre-generate
    print("Pre-generating objects...")
    objects = [
        BenchMsg(
            timestamp=123456789 + i, 
            val1=i*0.1, 
            val2=i*0.5, 
            status=i%255, 
            flags=i%65535
        ) 
        for i in range(COUNT)
    ]
    
    # 2. Serialization Test
    print("Starting Serialization...")
    t0 = time.time()
    
    # Serialize all to a single buffer (simulation of throughput)
    # Using list comprehension inside join for speed, or bytearray extend
    # Let's simply iterate and call serialize to measure the *overhead* of the engine
    
    # Create a sink (preallocated if possible, but python bytearray extend is fast)
    # To be fair, we just want to measure the .serialize() call time.
    
    # data_list = [obj.serialize() for obj in objects] 
    # The above includes list build time. 
    
    # Let's do a loop
    data_out = bytearray()
    
    t_start = time.perf_counter()
    for obj in objects:
        data_out.extend(obj.serialize())
    t_end = time.perf_counter()
    
    duration = t_end - t_start
    tps = COUNT / duration
    print(f"Serialization Time: {duration:.4f} sec")
    print(f"Throughput: {tps:,.2f} msgs/sec")
    
    # 3. Deserialization Test
    print("\nStarting Deserialization...")
    # We have 'data_out'. Let's parse it all back.
    # We can use Registry.deserialize in a loop if we knew offsets, 
    # OR simpler: use StreamHandler/Message.from_bytes but `from_bytes` assumes we sliced it.
    
    # To test RAW deserialization speed without 'StreamHandler' buffering overhead:
    # We need to know the size. BenchMsg is fixed size? 
    # U64(8) + F32(4) + F32(4) + U8(1) + U16(2) = 19 bytes.
    # BenchMsg is fixed size.
    
    msg_size = 19
    full_bytes = bytes(data_out)
    
    t_start = time.perf_counter()
    
    offset = 0
    limit = len(full_bytes)
    
    decoded_count = 0
    while offset < limit:
        # Simulate extraction (slicing overhead is part of python)
        # In C++ we'd just cast pointer. In Python struct.unpack_from is best.
        # But our API is BenchMsg.from_bytes(data). 
        # from_bytes takes bytes.
        
        chunk = full_bytes[offset : offset+msg_size] # Slice
        msg, cons = BenchMsg.from_bytes(chunk)
        offset += cons
        decoded_count += 1
        
    t_end = time.perf_counter()
    
    duration = t_end - t_start
    tps = COUNT / duration
    print(f"Deserialization Time: {duration:.4f} sec")
    print(f"Throughput: {tps:,.2f} msgs/sec")
    
    assert decoded_count == COUNT

if __name__ == "__main__":
    run_benchmark()
