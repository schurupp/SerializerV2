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
    value: int

@dataclass
class EnumDefinition:
    name: str = "NewEnum"
    items: List[EnumItem] = field(default_factory=list)

@dataclass
class SPLDefinition:
    name: str = "Config_A"

@dataclass
class MessageDefinition:
    name: str = "NewMessage"
    fields: List[FieldDefinition] = field(default_factory=list)
    active_configs: List[str] = field(default_factory=list) # List of SPL names this message belongs to (empty=ALL)

@dataclass
class ProjectDefinition:
    messages: List[MessageDefinition] = field(default_factory=list)
    enums: List[EnumDefinition] = field(default_factory=list)
    spl_configs: List[SPLDefinition] = field(default_factory=list) # Global list of SPL tags
