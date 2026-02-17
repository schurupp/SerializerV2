from serializer_core import *
from .enums import *


@register
class saddsadsa(StringMessage):
    protocol_mode = "string"
    endianness = '<'
    cmd_type = StringField(default='CMD', size_mode='Dynamic', is_discriminator=True)
    cmd_str = StringField(default='SUB', size_mode='Dynamic', is_discriminator=True)
    new_field = EnumField(NewEnum, storage_type='String', default='sad', is_discriminator=False)
