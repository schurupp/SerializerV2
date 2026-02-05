from serializer_core import *
from .enums import *


@register
class test(StringMessage):
    cmd_type = StringField(default='RET', size_mode='Dynamic')
    cmd_str = StringField(default='PING', size_mode='Dynamic')
