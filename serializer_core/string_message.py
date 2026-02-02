from typing import Tuple, Dict, Any
from .messages import Message
from .protocols import ProtocolConfig
from .fields import Field, StringField, EnumField
from .checksums import calculate # If we use checksums

class StringMessage(Message):
    """
    Base class for ASCII/String protocol messages.
    Format: <ID|CMD|FIELD1;FIELD2...>
    """
    protocol_mode = "string"
    
    # These must be defined by subclass or generator
    # but we can enforce them checking fields
    
    msg_id: int = 0

    def serialize(self) -> bytes:
        config = ProtocolConfig.get()
        start = config.START_SYMBOL
        end = config.END_SYMBOL
        
        # 1. Header Construction
        # Format: <MSG_ID><DELIM_ID><CMD_TYPE><DELIM_TYPE><CMD><DELIM_CMD>
        
        # Retrieve system fields
        _msg_id_str = f"{self.msg_id:04X}"
        
        # Retrieve mandatory fields (CMD_TYPE, CMD)
        # We assume fields 'cmd_type' and 'cmd_str' exist.
        if not hasattr(self, 'cmd_type') or not hasattr(self, 'cmd_str'):
             # Fallback or Error? 
             # For robustness, try to find first 2 fields or empty?
             # Spec says they are mandatory.
             c_type = getattr(self, 'cmd_type', "UNK")
             c_cmd = getattr(self, 'cmd_str', "UNK")
        else:
             c_type = self.fields['cmd_type'].to_string(self.cmd_type)
             c_cmd = self.fields['cmd_str'].to_string(self.cmd_str)
             
        # Build Header
        # MSG_ID + DELIM_ID + CMD_TYPE + DELIM_TYPE + CMD + DELIM_CMD
        header_str = (
            f"{_msg_id_str}{config.DELIM_ID}"
            f"{c_type}{config.DELIM_TYPE}"
            f"{c_cmd}{config.DELIM_CMD}"
        )
        
        # 2. Body Construction
        # Iterate all OTHER fields
        body_parts = []
        skip_names = ['cmd_type', 'cmd_str']
        
        for name, field in self.fields.items():
            if name in skip_names: continue
            if field.is_checksum: continue
            
            val = getattr(self, name)
            body_parts.append(field.to_string(val))
            
        # Format: F1<DELIM_FIELD>F2<DELIM_FIELD>...
        body_str = ""
        for part in body_parts:
            body_str += f"{part}{config.DELIM_FIELD}"
            
        # 3. Assemble for Checksum
        # "defined from the START to the last FIELD_DELIMITER in front of the CHECKSUM"
        # So: START + HEADER + BODY
        content_to_hash = f"{start}{header_str}{body_str}"
        
        # 4. Checksum
        # Fixed 2 digit hex.
        # Calc simplistic sum or xor for now (since no config for algorithms yet)
        # Or Just placeholder '00' if USE_CHECKSUM is True
        
        chk_str = ""
        if config.USE_CHECKSUM:
            # Simple XOR checksum of bytes
            chk_val = 0
            for b in content_to_hash.encode('utf-8'):
                chk_val ^= b
            chk_str = f"{chk_val:02X}"
        
        full_msg = f"{content_to_hash}{chk_str}{end}"
        return full_msg.encode('utf-8')

    @classmethod
    def from_bytes(cls, data: bytes) -> Tuple['StringMessage', int]:
        config = ProtocolConfig.get()
        start = config.START_SYMBOL.encode('utf-8')
        end = config.END_SYMBOL.encode('utf-8')
        
        try:
            start_idx = data.index(start)
            end_idx = data.index(end, start_idx)
        except ValueError:
            raise ValueError("Start/End symbols not found")
            
        full_len = end_idx + len(end)
        
        # Extract content between START and END
        # Actually content includes start? "from START to..."
        # Serialization: START + CONTENT + CHECKSUM + END
        # So blob is: data[start_idx : end_idx]
        
        blob = data[start_idx : end_idx].decode('utf-8')
        # blob = "<0000|LOG|SYS|A;B;CS" (example)
        
        # Strip START
        if not blob.startswith(config.START_SYMBOL):
            raise ValueError("Invalid Start Symbol during decode")
            
        # Remove Start
        inner = blob[len(config.START_SYMBOL):]
        # inner = "0000|LOG|SYS|A;B;CS"
        
        # Extract Checksum (last 2 chars)
        if config.USE_CHECKSUM:
            if len(inner) < 2: raise ValueError("Message too short for checksum")
            chk_rec = inner[-2:]
            inner = inner[:-2] # Remove checksum from content
            # Verify? (Optional for now)
            
        # Now parse: MSG_ID + DELIMS + FIELDS
        # Strict parsing
        
        # 1. MSG_ID (first occurrence of DELIM_ID)
        try:
            split1 = inner.split(config.DELIM_ID, 1)
            msg_id_str = split1[0]
            rest = split1[1]
            
            # 2. CMD_TYPE (search DELIM_TYPE)
            split2 = rest.split(config.DELIM_TYPE, 1)
            cmd_type_str = split2[0]
            rest = split2[1]
            
            # 3. CMD (search DELIM_CMD)
            split3 = rest.split(config.DELIM_CMD, 1)
            cmd_str = split3[0]
            body_blob = split3[1]
            
        except IndexError:
            raise ValueError("Malformed String Message: Missing Delimiters")
            
        # Instantiate
        obj = cls()
        try:
            obj.msg_id = int(msg_id_str, 16)
        except:
             pass 
             
        # Set Header Fields
        # We need to map 'cmd_type_str' -> 'cmd_type' field (Enum or String)
        if 'cmd_type' in cls.fields:
             val = cls._parse_value(cls.fields['cmd_type'], cmd_type_str)
             setattr(obj, 'cmd_type', val)
        if 'cmd_str' in cls.fields:
             val = cls._parse_value(cls.fields['cmd_str'], cmd_str)
             setattr(obj, 'cmd_str', val)
             
        # Body Parsing
        # body_blob = "F1;F2;"
        # Split by DELIM_FIELD
        if body_blob:
            parts = body_blob.split(config.DELIM_FIELD)
            # Last part might be empty string due to trailing delimiter
            if parts and parts[-1] == "":
                parts.pop()
                
            body_fields = [n for n in cls.fields.keys() if n not in ['cmd_type', 'cmd_str'] and not cls.fields[n].is_checksum]
            
            for i, val_str in enumerate(parts):
                if i < len(body_fields):
                    f_name = body_fields[i]
                    f_field = cls.fields[f_name]
                    val = cls._parse_value(f_field, val_str)
                    setattr(obj, f_name, val)
                    
        return obj, full_len

    @staticmethod
    def _parse_value(field, val_str):
        # Helper to convert "100" -> 100 or "ACK" -> Enum.ACK
        if isinstance(field, EnumField):
             # Try to find member by Name
             try:
                 return field.enum_cls[val_str]
             except KeyError:
                 # Try value
                 try:
                     return field.enum_cls(int(val_str))
                 except:
                     return val_str # Fallback
        elif isinstance(field, StringField):
            return val_str
        # Primitives?
        # Field.from_string? We didn't implement from_string!
        # Assume int/float conversion if needed
        try:
             if hasattr(field, 'fmt_char'):
                 if field.fmt_char in 'fd': return float(val_str)
                 return int(val_str)
        except:
             return val_str
        return val_str
