# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Raspberry Pi Sense HAT Emulator library for the Raspberry Pi
# Copyright (c) 2016 Raspberry Pi Foundation <info@raspberrypi.org>
#
# This package is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This package is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )
nstr = str
str = type('')

import io
import errno
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


def slow_pi():
    """
    Returns ``True`` if the local hardware is a Raspberry Pi with a slow
    processor, specifically a BCM2835. This is used to determine defaults for
    the simulation's processing.
    """
    try:
        cpu = ''
        with io.open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Hardware'):
                    cpu = line.split(':', 1)[1].strip()
                    break
        return cpu in ('BCM2835', 'BCM2708')
    except IOError as e:
        if e.errno == errno.ENOENT:
            return False
        raise

