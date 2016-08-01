# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Raspberry Pi Sense HAT Emulator library for the Raspberry Pi
# Copyright (c) 2016 Raspberry Pi Foundation <info@raspberrypi.org>
#
# All Rights Reserved.

from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )
nstr = str
str = type('')


from struct import Struct
from collections import namedtuple


# Structures for sense_rec and sense_play
HEADER_REC = Struct(nstr(
    '='  # native order, standard sizing
    '8s' # magic number ("SENSEHAT")
    'b'  # version number (1)
    '7x' # padding
    'd'  # initial timestamp
    ))

DATA_REC = Struct(nstr(
    '='   # native order, standard sizing
    'd'   # timestamp
    'dd'  # pressure+temp readings
    'dd'  # humidity+temp readings
    'ddd' # raw accelerometer readings
    'ddd' # raw gyro readings
    'ddd' # raw compass readings
    'ddd' # calculated pose
    ))

DataRecord = namedtuple('DataRecord', (
    'timestamp',
    'pressure', 'ptemp',
    'humidity', 'htemp',
    'ax', 'ay', 'az',
    'gx', 'gy', 'gz',
    'cx', 'cy', 'cz',
    'ox', 'oy', 'oz',
    ))


def clamp(value, min_value, max_value):
    """
    Return *value* clipped to the range *min_value* to *max_value* inclusive.
    """
    return min(max_value, max(min_value, value))

