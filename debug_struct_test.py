import struct
try:
    fmt = '<B<I<I'
    print(f"Testing format: '{fmt}'")
    s = struct.Struct(fmt)
    print("Success")
except Exception as e:
    print(f"Fail: {e}")

try:
    fmt2 = 'BII'
    print(f"Testing format: '{fmt2}'")
    s = struct.Struct(fmt2)
    print("Success 2")
except Exception as e:
    print(f"Fail 2: {e}")
