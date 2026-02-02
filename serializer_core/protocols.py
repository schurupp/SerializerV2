from dataclasses import dataclass

@dataclass
class ProtocolConfig:
    START_SYMBOL: str = "<"
    END_SYMBOL: str = ">"
    DELIM_FIELD: str = ";"
    
    # Granular Delimiters
    DELIM_ID: str = "|"
    DELIM_TYPE: str = "|"
    DELIM_CMD: str = "|"
    
    USE_CHECKSUM: bool = True # Default true for V2?
    
    # Singleton instance
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def configure(cls, start="<", end=">", delim_field=";", delim_id="|", delim_type="|", delim_cmd="|", use_checksum=True):
        inst = cls.get()
        inst.START_SYMBOL = start
        inst.END_SYMBOL = end
        inst.DELIM_FIELD = delim_field
        inst.DELIM_ID = delim_id
        inst.DELIM_TYPE = delim_type
        inst.DELIM_CMD = delim_cmd
        inst.USE_CHECKSUM = use_checksum
