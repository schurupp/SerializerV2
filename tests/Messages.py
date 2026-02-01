from serializer_core import *
from enums import *


@register
class TestMsg1(Message):
    message_id = UInt16(default=100, is_discriminator=True)
    message_size = UInt16(default=6)
    timestamp = UInt32(default=0, is_timestamp=True)

@register
class TestMsg2(Message):
    message_id = UInt16(default=150, is_discriminator=True)
    message_size = UInt16(default=0)
    timestamp = UInt32(default=0, is_timestamp=True)
    working_mode = EnumField(enum_cls=WorkingMode, default=0)

@register
class TestMsg3(Message):
    message_id = UInt16(default=200, is_discriminator=True)
    message_size = UInt16(default=0)
    timestamp = UInt32(default=0, is_timestamp=True)
    gps_pos = FixedPointField(default=0.0, integer_bits=12, fractional_bits=4, encoding=2)
