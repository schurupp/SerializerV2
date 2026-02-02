from typing import Dict, Type, Tuple, Optional, Any, List
import struct

class Registry:
    _messages: Dict[int, Type['Message']] = {}
    _message_configs: Dict[int, List[str]] = {} # Map discriminator -> [allowed_configs]
    _message_offsets: Dict[int, int] = {} # Map discriminator -> offset from start
    
    # Optimization: Map[Offset, Map[Value, MessageClass]]
    _lookup_map: Dict[int, Dict[int, Type['Message']]] = {}
    
    # String Protocol Map: (cmd_type_str, cmd_str) -> MessageClass
    _string_messages: Dict[Tuple[str, str], Type['Message']] = {}

    _active_system_config: str = None # The global active config for this process
    
    @classmethod
    def set_active_config(cls, config_id: str):
        """Sets the active system configuration (SPL)."""
        cls._active_system_config = config_id

    @classmethod
    def register(cls, msg_cls: Type['Message'], config_id: str = None):
        """
        Registers a message class.
        Calculates the byte offset of the discriminator field.
        """
        # String Protocol Registration
        if getattr(msg_cls, 'protocol_mode', 'binary') == 'string':
             # Validate String Message
             defaults = {}
             for name in ['cmd_type', 'cmd_str']:
                 if name not in msg_cls.fields:
                     raise ValueError(f"StringMessage {msg_cls.__name__} missing required field '{name}'")
                 f = msg_cls.fields[name]
                 if f.default is None:
                     raise ValueError(f"StringMessage {msg_cls.__name__} field '{name}' must have a default value (discriminator).")
                 
                 val = f.default
                 if hasattr(f, 'enum_cls'): # Enum
                     # Try to get member name if default is int
                     if isinstance(val, int):
                         try:
                             val = f.enum_cls(val).name
                         except:
                             val = str(val)
                     elif hasattr(val, 'name'):
                         val = val.name
                     else:
                         val = str(val)
                 else:
                     val = str(val)
                 defaults[name] = val
                 
             key = (defaults['cmd_type'], defaults['cmd_str'])
             cls._string_messages[key] = msg_cls
             return

        # 1. Find Discriminator and Calculate Offset
        disc_value = None
        disc_offset = 0
        found_disc = False
        
        for name, field in msg_cls.fields.items():
            if field.is_discriminator:
                if field.default is None:
                    raise ValueError(f"Message {msg_cls.__name__} discriminator field '{name}' must have a default value.")
                disc_value = field.default
                found_disc = True
                break
            
            # Add size of preceding field
            # Must be fixed size!
            try:
                # Use struct size if available
                if field.struct_format:
                    s = struct.Struct(field.struct_format) # Use cached if possible? Field usually caches it.
                    disc_offset += s.size
                elif hasattr(field, '_struct') and field._struct:
                     disc_offset += field._struct.size
                else:
                    # Complex generic? 
                    # If it's a fixed array of complex items, we might support it if we implement size property?
                    # For now, if no struct_format, assume dynamic/unknown -> fail.
                    raise ValueError(f"Field '{name}' preceding discriminator in {msg_cls.__name__} must be fixed size.")
            except Exception as e:
                 raise ValueError(f"Cannot calculate offset for discriminator in {msg_cls.__name__}. Preceding field '{name}' is dynamic or unknown size: {e}")

        if found_disc and disc_value is not None:
             # Store in main dict (disc -> cls) - Note: Disc collision with diff offsets?
             # If two messages have same Disc but diff Offset, _messages[disc] collision!
             # But usually Discriminator Value is Unique in the system?
             # User requirement: "If multiple messages share a discriminator value but at different offsets..."
             # This implies Disc Value is NOT unique globally, but (Offset, Value) tuple IS unique?
             
             if cls._active_system_config and config_id and config_id != cls._active_system_config:
                 return # Skip registration if config mismatch
                 
             cls._messages[disc_value] = msg_cls
             cls._message_offsets[disc_value] = disc_offset
             
             # Populate Optimized Lookup
             if disc_offset not in cls._lookup_map:
                 cls._lookup_map[disc_offset] = {}
             cls._lookup_map[disc_offset][disc_value] = msg_cls
             
             # Configs
             current_list = cls._message_configs.get(disc_value, [])
             if config_id:
                 if config_id not in current_list:
                     current_list.append(config_id)
                 cls._message_configs[disc_value] = current_list
             else:
                 if not current_list:
                     cls._message_configs[disc_value] = []

    @classmethod
    def deserialize(cls, data: bytes, message_set: Optional[str] = None) -> Tuple[Any, int]:
        """
        Smart Deserialization using Offsets.
        """
        if not data:
            return None, 0
            
        # Check for String Protocol
        from .protocols import ProtocolConfig
        p_cfg = ProtocolConfig.get()
        start_sym = p_cfg.START_SYMBOL.encode('utf-8')
        
        if data.startswith(start_sym):
            return cls.deserialize_string(data)
            
        target_config = message_set if message_set else cls._active_system_config
        
        incomplete_data = False
        
        for offset, val_map in cls._lookup_map.items():
            if len(data) > offset:
                for disc_val, msg_cls in val_map.items():
                    # Check SPL
                    allowed = cls._message_configs.get(disc_val, [])
                    if allowed and target_config:
                        if target_config not in allowed:
                            continue

                    disc_field = None
                    for f in msg_cls.fields.values():
                        if f.is_discriminator:
                            disc_field = f
                            break
                    
                    if disc_field:
                         try:
                             peek_data = data[offset:]
                             val, _ = disc_field.from_bytes(peek_data)
                             
                             if val == disc_val:
                                 # Found match, try full deserialize
                                 # If full deserialize fails due to size, it will raise struct.error
                                 # which is what we want (propagated up).
                                 val, consumed = msg_cls.from_bytes(data)
                                 return val, consumed
                         except (ValueError, struct.error, IndexError):
                             incomplete_data = True
                             continue
            else:
                incomplete_data = True
                
        if incomplete_data:
            # We checked what we could, and some checks were skipped or failed due to size.
            raise struct.error("Incomplete data for potential candidates.")
            
        raise struct.error("Unknown message (discriminator not found)")

    @classmethod
    def deserialize_string(cls, data: bytes) -> Tuple[Any, int]:
        from .protocols import ProtocolConfig
        cfg = ProtocolConfig.get()
        # Ensure delimiters are loaded
        delim_id = cfg.DELIM_ID
        delim_type = cfg.DELIM_TYPE
        delim_cmd = cfg.DELIM_CMD
        
        start_sym = cfg.START_SYMBOL.encode('utf-8')
        end_sym = cfg.END_SYMBOL.encode('utf-8')
        
        try:
            # Find boundaries
            s_idx = data.index(start_sym)
            e_idx = data.index(end_sym, s_idx)
            
            # Extract content (excluding START, but including everything else up to END)
            content_bytes = data[s_idx + len(start_sym) : e_idx]
            content = content_bytes.decode('utf-8')
            
            # Parse Header strictly: <MSG_ID><DELIM_ID><CMD_TYPE><DELIM_TYPE><CMD><DELIM_CMD>
            
            # 1. Split ID
            parts1 = content.split(delim_id, 1)
            if len(parts1) < 2: raise ValueError("Missing ID Delimiter")
            # msg_id_str = parts1[0] # Not used for lookup
            rest = parts1[1]
            
            # 2. Split CMD_TYPE
            parts2 = rest.split(delim_type, 1)
            if len(parts2) < 2: raise ValueError("Missing TYPE Delimiter")
            cmd_type = parts2[0]
            rest = parts2[1]
            
            # 3. Split CMD
            parts3 = rest.split(delim_cmd, 1)
            # if len(parts3) < 2: ... # Actually body might be empty, so strict check?
            # "CMD><DELIM_CMD><FIELDS..."
            # Yes, delimiter implies it exists.
            if len(parts3) < 2: raise ValueError("Missing CMD Delimiter")
            cmd_str = parts3[0]
            
            # Lookup
            key = (cmd_type, cmd_str)
            
            if key in cls._string_messages: # Changed from _string_registry to _string_messages to match class definition
                msg_cls = cls._string_messages[key]
                return msg_cls.from_bytes(data)
            else:
                # Fallback: Try looking up by just one if logic dictates? 
                # Currently strict lookup on (type, cmd)
                # Maybe try default if not found?
                pass
                
            raise struct.error(f"Unknown string message: {key}")
            
        except (ValueError, IndexError) as e:
            # Malformed or not found
            raise struct.error(f"String Parse Error: {e}")
