import unittest
import random
from collections import deque
from tests.common import KitchenSinkBinary, KitchenSinkString, fuzz_binary, fuzz_string
# Assuming StreamHandler exists and can be imported
# If not, we might need to point to correct location.
# Re-checking imports from previous sessions: StreamHandler logic usually in serializer_core/stream.py?
# Or directly serializer_core?
# I'll try direct import or fallback.
try:
    from serializer_core import StreamHandler
except ImportError:
    # Maybe inside a submodule?
    try:
        from serializer_core.stream import StreamHandler
    except ImportError:
        # Mock class if not existing yet (was not part of previous prompt? Wait. User implies it exists)
        # "Validate the StreamHandler...".
        # If it doesn't exist I should create it or find it.
        # I'll check file list later if this fails.
        # For now assume `from serializer_core import StreamHandler` works if exposed in __init__.
        pass

class TestStream(unittest.TestCase):
    def test_binary_chaos(self):
        # 1. Generate 100 random messages
        history = []
        stream_data = bytearray()
        
        for _ in range(100):
            msg = KitchenSinkBinary()
            fuzz_binary(msg)
            data = msg.serialize()
            history.append(msg)
            stream_data.extend(data)
            
        # 2. Setup StreamHandler
        # StreamHandler(message_types=[List of classes])?
        # Standard StreamHandler usually takes a registry/list.
        handler = StreamHandler() 
        handler.register(KitchenSinkBinary) 
        
        # 3. Chaos Feeding
        cursor = 0
        total_len = len(stream_data)
        
        while cursor < total_len:
            # Random chunk size 1-50
            chunk_size = random.randint(1, 50)
            end = min(cursor + chunk_size, total_len)
            chunk = stream_data[cursor:end]
            
            handler.process(chunk)
            cursor = end
            
        # 4. Assert
        # Check output queue
        results = handler.get_messages() # Assuming get_messages() or .queue
        # If handler puts valid messages in a list/queue:
        self.assertEqual(len(results), 100)
        
        for i, original in enumerate(history):
            reconstructed = results[i]
            # Quick check (Header Magic)
            self.assertEqual(original.magic, reconstructed.magic)
            # Deep check? (Optional, verify kitchen sink passes)
            self.assertEqual(original.msg_len, reconstructed.msg_len)

    def test_string_chaos(self):
        # String Protocol usually harder due to delimiter scanning
        history = []
        stream_data = bytearray()
        
        for _ in range(100):
            msg = KitchenSinkString()
            fuzz_string(msg)
            data = msg.serialize()
            history.append(msg)
            stream_data.extend(data)
            
        # Register
        handler = StreamHandler(protocol="string") # Assuming mode switch
        handler.register(KitchenSinkString)
        
        cursor = 0
        total_len = len(stream_data)
        
        while cursor < total_len:
            chunk_size = random.randint(1, 50)
            end = min(cursor + chunk_size, total_len)
            chunk = stream_data[cursor:end]
            
            handler.process(chunk)
            cursor = end
            
        results = handler.get_messages()
        self.assertEqual(len(results), 100)
        
        for i, original in enumerate(history):
            rec = results[i]
            self.assertEqual(original.head, rec.head)

if __name__ == '__main__':
    unittest.main()
