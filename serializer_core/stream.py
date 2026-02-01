from typing import Any, Deque, Optional
import struct
from .registry import Registry

class StreamHandler:
    """
    Manages incoming byte streams (TCP sticky packets).
    Buffers data and extracts complete messages.
    """
    def __init__(self):

        self._buffer = bytearray()

    def feed(self, data: bytes, target_deque: Deque[Any], message_set: Optional[str] = None):
        """
        Feed new data into the handler.
        Deserialized messages are appended to target_deque.
        """
        if not data:
            return

        self._buffer.extend(data)
        
        while True:
            view = memoryview(self._buffer)
            # Must capture result variables outside try to ensuring scoping if we split logic?
            # Or just release view inside each path.
            
            # Use a flag to track if we should break or continue, 
            # dragging logic out of the 'view' scope.
            
            result_obj = None
            result_consumed = 0
            resync_needed = False
            error_break = False
            
            try:
                obj, consumed = Registry.deserialize(view, message_set=message_set)
                if obj:
                    result_obj = obj
                    result_consumed = consumed
                else:
                    resync_needed = True
                    
            except (ValueError, struct.error):
                # Not enough data
                error_break = True
            except Exception as e:
                print(f"StreamHandler Error: {e}")
                import traceback
                traceback.print_exc()
                resync_needed = True # Try to skip bad byte?
                
            view.release()
            
            if result_obj:
                target_deque.append(result_obj)
                del self._buffer[:result_consumed]
                continue
                
            if error_break:
                break
                
            if resync_needed:
                if len(self._buffer) > 0:
                     # print(f"Skip: {hex(self._buffer[0])}")
                     del self._buffer[:1]
                     continue
                else:
                     break
            
            # Default break if nothing happened (should be covered)
            break
