from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class FieldDefinition:
    name: str = "new_field"
    field_type: str = "UInt32"
    # Options now hold: is_discriminator, is_checksum, default_value, active_configs, etc.
    options: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EnumItem:
    name: str
    value: Any # int or str

@dataclass
class EnumDefinition:
    name: str = "NewEnum"
    storage_type: str = "UInt32"
    items: List[EnumItem] = field(default_factory=list)
    active_configs: List[str] = field(default_factory=list)

@dataclass
class SPLDefinition:
    name: str = "Config_A"

@dataclass
class MessageDefinition:
    name: str = "NewMessage"
    fields: List[FieldDefinition] = field(default_factory=list)
    active_configs: List[str] = field(default_factory=list) # List of SPL names this message belongs to (empty=ALL)
    protocol_mode: str = "binary" # "binary" or "string"
    endianness: str = "Inherit" # Inherit, Little, Big

@dataclass
class ProjectDefinition:
    name: str = "NewProject"
    messages: List[MessageDefinition] = field(default_factory=list)
    enums: List[EnumDefinition] = field(default_factory=list)
    spl_configs: List[SPLDefinition] = field(default_factory=list) # Global list of SPL tags
    protocol_mode: str = "binary" # "binary" or "string"
    global_endianness: str = "Little" # Little, Big
