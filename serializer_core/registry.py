from typing import Dict, Type, Tuple, Optional, Any, List
import struct

class Registry:
    _messages: Dict[int, Type['Message']] = {}
    _message_configs: Dict[int, List[str]] = {} # Map discriminator -> [allowed_configs]
    
    _active_system_config: str = None # The global active config for this process
    
    @classmethod
    def set_active_config(cls, config_id: str):
        """Sets the active system configuration (SPL)."""
        cls._active_system_config = config_id

    @classmethod
    def register(cls, msg_cls: Type['Message'], config_id: str = None):
        """
        Registers a message class.
        """
        # 1. Find Discriminator
        disc_value = None
        for name, field in msg_cls.fields.items():
            if field.is_discriminator:
                if field.default is None:
                    raise ValueError(f"Message {msg_cls.__name__} discriminator field '{name}' must have a default value.")
                disc_value = field.default
                break
        
        if disc_value is not None:
            # 2. Check Config collision?
            # We allow the same ID if configs are disjoint?
            # For simplicity, we just store it.
            
            # SPL Filtering Optimization:
            # If we knew the config NOW, we could skip.
            # But usually config is set at startup (runtime).
            
            cls._messages[disc_value] = msg_cls
            current_list = cls._message_configs.get(disc_value, [])
            
            if config_id:
                if config_id not in current_list:
                    current_list.append(config_id)
                cls._message_configs[disc_value] = current_list
            else:
                # If config_id is None, it means Global/All?
                # If we mix Explicit Configs and None...
                # Current logic: If allowed=[], check skipped.
                # If we have [A, B], check enforces.
                # If we add None? -> [] ?
                # If a message is defined as "Global", it overrides specific configs?
                # Usually if "Global" is present, the list should be effectively clear?
                pass 
                # Don't overwrite if existing configs present from other decorators?
                # If ONLY @register (None) is used, then list is empty.
                if not current_list:
                    cls._message_configs[disc_value] = []

    @classmethod
    def deserialize(cls, data: bytes, message_set: Optional[str] = None) -> Tuple[Any, int]:
        """
        Smart Deserialization.
        message_set arg (SPL tag) overrides global config?
        """
        if not data:
            return None, 0
            
        # Target Config
        target_config = message_set if message_set else cls._active_system_config
            
        # Try UInt8 Discriminator
        if len(data) > 0:
            val8 = data[0]
            if val8 in cls._messages:
                # SPL Check
                allowed = cls._message_configs.get(val8, [])
                if allowed and target_config:
                    if target_config not in allowed:
                        return None, 0
                
                msg_cls = cls._messages[val8]
                return msg_cls.from_bytes(data)
            else:
                 print(f"Registry: Unknown discriminator {hex(val8)}. Known: {[hex(k) for k in cls._messages.keys()]}")
                 pass

        return None, 0
