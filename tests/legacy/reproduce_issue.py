import sys
import os

# Ensure root in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from tests.common import KitchenSinkBinary, fuzz_binary
    for i in range(100):
        obj = KitchenSinkBinary()
        fuzz_binary(obj)
        data = obj.serialize()
    print("Serialized 100 times successfully.")
except Exception as e:
    import traceback
    traceback.print_exc()
