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

import sys
import os
import io
import mmap
import errno
import subprocess
from struct import Struct
from collections import namedtuple, deque
from random import Random
from time import time
from threading import Thread, Lock, Event
try:
    from statistics import mean
except ImportError:
    from .compat import mean

from .common import clamp


IMU_DATA = Struct(
    '<'   # little endian
    'B'   # IMU sensor type
    '20p' # IMU sensor name
    )

IMUData = namedtuple('IMUData',
    ('type', 'name', 'accel', 'gyro', 'compass'))


def imu_filename():
    """
    Return the filename used represent the state of the emulated sense HAT's
    IMU sensors. On UNIX we try ``/dev/shm`` then fall back to ``/tmp``; on
    Windows we use whatever ``%TEMP%`` contains
    """
    fname = 'rpi-sense-emu-imu'
    if sys.platform.startswith('win'):
        # just use a temporary file on Windows
        return os.path.join(os.environ['TEMP'], fname)
    else:
        if os.path.exists('/dev/shm'):
            return os.path.join('/dev/shm', fname)
        else:
            return os.path.join('/tmp', fname)


def init_imu():
    """
    Opens the file representing the state of the IMU sensors. The file-like
    object is returned.

    If the file already exists we simply make sure it is the right size. If
    the file does not already exist, it is created and zeroed.
    """
    try:
        # Attempt to open the IMU's device file and ensure it's the right size
        fd = io.open(imu_filename(), 'r+b', buffering=0)
        fd.seek(IMU_DATA.size)
        fd.truncate()
    except IOError as e:
        # If the screen's device file doesn't exist, create it with reasonable
        # initial values
        if e.errno == errno.ENOENT:
            fd = io.open(imu_filename(), 'w+b', buffering=0)
            fd.write(b'\x00' * IMU_DATA.size)
        else:
            raise
    return fd


