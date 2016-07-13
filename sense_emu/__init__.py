from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )

from .sense_hat import SenseHat, SenseHat as AstroPi
from .stick import (
    SenseStick,
    DIRECTION_UP,
    DIRECTION_DOWN,
    DIRECTION_LEFT,
    DIRECTION_RIGHT,
    DIRECTION_MIDDLE,
    ACTION_PRESSED,
    ACTION_RELEASED,
    ACTION_HELD,
    )

__version__ = '2.2.0'
