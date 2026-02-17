import argparse
import importlib.util
import inspect
import random
import os
import sys
import struct

# Ensure root in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from serializer_core import Message, StringMessage, register

def load_module_from_path(path):
    spec = importlib.util.spec_from_file_location("user_module", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["user_module"] = module
    spec.loader.exec_module(module)
    return module

def fuzz_object(obj):
    # Dynamic Fuzzing based on fields
    # Inspect obj.fields
    if hasattr(obj, 'fields'):
        for name, field in obj.fields.items():
            # Primitive mapping?
            # Field classes don't easily expose their 'type' as a simple enum.
            # We check class name.
            ftype = field.__class__.__name__
            
            val = 0
            if 'UInt' in ftype:
                # UInt8, UInt16...
                # Guess size or strict?
                # struct_format?
                # Quick hack: 0-100
                val = random.randint(0, 100)
            elif 'Int' in ftype:
                val = random.randint(-50, 50)
            elif 'Float' in ftype:
                val = random.random() * 100.0
            elif 'Double' in ftype:
                val = random.random() * 100.0
            elif 'Bool' in ftype:
                val = random.choice([True, False])
            elif 'StringField' == ftype:
                val = "TEST_" + str(random.randint(0, 99))
            elif 'EnumField' == ftype:
                # Need enum type
                # field.enum_type (from backend props)?
                # If available pick random. Else 0.
                if hasattr(field, 'enum_type') and field.enum_type:
                    try:
                        opts = list(field.enum_type)
                        val = random.choice(opts)
                    except:
                        val = 0
                else:
                    val = 0
            
            # ArrayField? Nested?
            # Too complex for quick generic fuzzer without recursion.
            # Skip complex fields or set empty.
            
            # Set attr
            try:
                setattr(obj, name, val)
            except:
                pass

def run_tests(module_path):
    print(f"Loading {module_path}...")
    try:
        mod = load_module_from_path(module_path)
    except Exception as e:
        print(f"Failed to load module: {e}")
        return

    # Find Classes
    classes = []
    for name, cls in inspect.getmembers(mod, inspect.isclass):
        if issubclass(cls, Message) and cls is not Message and cls is not StringMessage:
            classes.append(cls)
            
    print(f"Found {len(classes)} Message classes.")
    
    for cls in classes:
        print(f"Testing {cls.__name__}...", end=" ")
        try:
            obj = cls()
            fuzz_object(obj)
            
            data = obj.serialize()
            
            rec = cls()
            rec.deserialize(data)
            
            # Simple check: re-serialize should match
            data2 = rec.serialize()
            if data == data2:
                 print("PASS")
            else:
                 print("FAIL (Mismatch)")
                 # Diff?
                 # print(f"  Orig: {data.hex()}")
                 # print(f"  Rec : {data2.hex()}")
                 
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generic Serializer Tester")
    parser.add_argument("file", help="Path to Python file containing Message definitions")
    args = parser.parse_args()
    
    run_tests(args.file)
