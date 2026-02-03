from serializer_core import *
from .enums import *


@register
class msg1(Message):
    endianness = '<'
    cmd_type = StringField(default='CMD', is_discriminator=True)
    cmd_str = StringField(default='SUB', is_discriminator=True)

@register
class msg2(Message):
    endianness = '<'
    cmd_type = StringField(default='CMD', is_discriminator=True)
    cmd_str = StringField(default='SUB', is_discriminator=True)
