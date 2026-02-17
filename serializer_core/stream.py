from typing import Any, Deque, Optional
import struct
from serializer_core.registry import Registry

class StreamHandler:
    """
    Manages incoming byte streams (TCP sticky packets).
    Buffers data and extracts complete messages.
    Supports BINARY, STRING, or AUTO (Legacy) modes.
    """
    def __init__(self, protocol_mode: str = "AUTO"):
        self._buffer = bytearray()
        self.protocol_mode = protocol_mode

    def feed(self, data: bytes, target_deque: Deque[Any], message_set: Optional[str] = None):
        """
        Feed new data into the handler.
        Deserialized messages are appended to target_deque.
        """
        if not data:
            return

        self._buffer.extend(data)
        
        while True:
            # We don't use memoryview for String Protocol usually, as it deals with 'bytes.decode' 
            # and regex/finding delimiters, which might copy anyway. 
            # But Registry.deserialize expects bytes-like.
            
            view = memoryview(self._buffer)
            
            result_obj = None
            result_consumed = 0
            resync_needed = False
            error_break = False
            
            try:
                if self.protocol_mode == "BINARY":
                    obj, consumed = Registry.deserialize(view, message_set=message_set)
                elif self.protocol_mode == "STRING":
                    obj, consumed = Registry.deserialize_string(view) # Assuming support for memoryview
                else:
                    # AUTO (Legacy / Unsafe) - Tries Binary, falls back? 
                    # Or peeks first byte?
                    # Original implementation was effectively Binary-biased but called 'Registry.deserialize' 
                    # which checked for String Protocol if it failed? No, Registry.deserialize 
                    # primarily does binary lookup by first byte.
                    obj, consumed = Registry.deserialize(view, message_set=message_set)

                if obj:
                    result_obj = obj
                    result_consumed = consumed
                else:
                    # Registry returned None? (e.g. unknown ID)
                    resync_needed = True
                    
            except (ValueError, struct.error) as e:
                # Not enough data (BINARY) or Incomplete Frame (STRING)
                # Ideally Registry raises specific "Incomplete" error vs "Corruption" error
                # For now, assume common errors mean "wait for more data"
                error_break = True
            except Exception as e:
                print(f"StreamHandler Error: {e}")
                # import traceback
                # traceback.print_exc()
                resync_needed = True 
                
            view.release()
            
            if result_obj:
                target_deque.append(result_obj)
                del self._buffer[:result_consumed]
                continue
                
            if error_break:
                break
                
            if resync_needed:
                if len(self._buffer) > 0:
                     # Skip 1 byte and retry (Brute force resync)
                     # For String Protocol, maybe skip to next '<'?
                     del self._buffer[:1]
                     continue
                else:
                     break
            
            break
