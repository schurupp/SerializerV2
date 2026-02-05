import time
import sys
import os

# Ensure root in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from tests.common import KitchenSinkBinary, KitchenSinkString, fuzz_binary, fuzz_string
from serializer_core import StreamHandler

def benchmark_binary_serialization(count=100000):
    print(f"Benchmarking Binary Serialization ({count} msgs)...")
    
    # Pre-generate 1 instance to avoid fuzzing overhead during measure
    # Or measure fuzzing too? Usually only serialize speed.
    # But usually different data is better.
    # Let's pre-generate data? Memory might be an issue for 100k objects?
    # 100k * 100 bytes = 10 MB. Safe.
    
    msgs = []
    for _ in range(count):
        m = KitchenSinkBinary()
        fuzz_binary(m)
        msgs.append(m)
        
    start = time.perf_counter()
    for m in msgs:
        m.serialize()
    end = time.perf_counter()
    
    duration = end - start
    rate = count / duration
    print(f"  Duration: {duration:.4f}s")
    print(f"  Rate: {rate:.2f} Msgs/Sec")
    print("-" * 30)

def benchmark_binary_stream(count=100000):
    print(f"Benchmarking Binary Stream Processing ({count} msgs)...")
    
    msgs = []
    # Reuse fuzz but we need bytes
    for _ in range(count):
        m = KitchenSinkBinary()
        fuzz_binary(m)
        msgs.append(m.serialize())
        
    # Combine into one stream (huge) or chunks?
    # Feeding 100k individual chunks simulates worse case than 1 huge chunk.
    # Let's feed individual msg bytes.
    
    handler = StreamHandler()
    handler.register(KitchenSinkBinary)
    
    start = time.perf_counter()
    for b in msgs:
        handler.process(b)
    end = time.perf_counter()
    
    # Verify processed
    # q = handler.get_messages()
    # assert len(q) == count
    
    duration = end - start
    rate = count / duration
    print(f"  Duration: {duration:.4f}s")
    print(f"  Rate: {rate:.2f} Msgs/Sec")
    print("-" * 30)

def benchmark_string_stream(count=100000):
    print(f"Benchmarking String Stream Processing ({count} msgs)...")
    
    msgs = []
    for _ in range(count):
        m = KitchenSinkString()
        fuzz_string(m)
        msgs.append(m.serialize())
        
    handler = StreamHandler(protocol="string")
    handler.register(KitchenSinkString)
    
    start = time.perf_counter()
    for b in msgs:
        handler.process(b)
    end = time.perf_counter()
    
    duration = end - start
    rate = count / duration
    print(f"  Duration: {duration:.4f}s")
    print(f"  Rate: {rate:.2f} Msgs/Sec")
    print("-" * 30)

if __name__ == "__main__":
    benchmark_binary_serialization()
    benchmark_binary_stream()
    benchmark_string_stream()
