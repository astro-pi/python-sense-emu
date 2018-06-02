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

import sys
import os
import io
import errno
import mmap
import struct
from threading import Thread, Event

import numpy as np


GAMMA_DEFAULT = [
    0,  0,  0,  0,  0,  0,  1,  1,
    2,  2,  3,  3,  4,  5,  6,  7,
    8,  9,  10, 11, 12, 14, 15, 17,
    18, 20, 21, 23, 25, 27, 29, 31]
GAMMA_LOW = [
    0,  1,  1,  1,  1,  1,  1,  1,
    1,  1,  1,  1,  1,  2,  2,  2,
    3,  3,  3,  4,  4,  5,  5,  6,
    6,  7,  7,  8,  8,  9,  10, 10]


def screen_filename():
    # returns the file used to represent the state of the emulated sense HAT's
    # screen. On UNIX we try /dev/shm then fall back to /tmp; on Windows we
    # use whatever %TEMP% points at
    fname = 'rpi-sense-emu-screen'
    if sys.platform.startswith('win'):
        # just use a temporary file on Windows
        return os.path.join(os.environ['TEMP'], fname)
    else:
        if os.path.exists('/dev/shm'):
            return os.path.join('/dev/shm', fname)
        else:
            return os.path.join('/tmp', fname)


def init_screen():
    try:
        # Attempt to open the screen's device file and ensure it's 160 bytes
        # long
        fd = io.open(screen_filename(), 'r+b', buffering=0)
        fd.seek(160)
        fd.truncate()
    except IOError as e:
        # If the screen's device file doesn't exist, create it with reasonable
        # initial values
        if e.errno == errno.ENOENT:
            fd = io.open(screen_filename(), 'w+b', buffering=0)
            fd.write(b'\x00\x00' * 64)
            fd.write(b''.join(chr(i).encode('ascii') for i in GAMMA_DEFAULT))
        else:
            raise
    return fd


class ScreenClient(object):
    def __init__(self):
        self._fd = init_screen()
        self._map = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_READ)
        # Construct arrays representing the LED states (_screen) and the user
        # controlled gamma lookup table (_gamma)
        self._screen = np.frombuffer(self._map, dtype=np.uint16, count=64).reshape((8, 8))
        self._gamma = np.frombuffer(self._map, dtype=np.uint8, count=32, offset=128)
        # Construct the final gamma correction lookup table. This is equivalent
        # to gamma correction of 1/4 (*much* brighter) because the HAT's RGB
        # LEDs are much brighter than a corresponding LCD display. It also uses
        # a non-zero starting point so that LEDs that are off appear gray
        self._gamma_rgbled = (
                np.sqrt(np.sqrt(np.linspace(0.05, 1, 32))) * 255
                ).astype(np.uint8)
        self._touch_stop = Event()
        self._touch_thread = Thread(target=self._touch_run)
        self._touch_thread.daemon = True
        self._touch_thread.start()

    def close(self):
        if self._fd:
            self._touch_stop.set()
            self._touch_thread.join()
            self._touch_thread = None
            self._map.close()
            self._map = None
            self._fd.close()
            self._fd = None

    def _touch_run(self):
        # "touch" the screen's frame-buffer once a second. This ensures that
        # the screen always updates at least once a second and works around the
        # issue that screen updates can be lost due to lack of resolution of
        # the file modification timestamps. Unfortunately, futimes(3) is not
        # universally supported, and only available in Python 3.3+ so this gets
        # a bit convoluted...
        touch = lambda: os.utime(self._fd.fileno())
        try:
            if os.utime in os.supports_fd:
                touch()
            else:
                raise NotImplementedError
        except (AttributeError, NotImplementedError) as e:
            touch = lambda: os.utime(self._fd.name, None)
        while not self._touch_stop.wait(1):
            touch()

    @property
    def array(self):
        return self._screen

    @property
    def rgb_array(self):
        a = np.empty((8, 8, 3), dtype=np.uint8)
        # convert the RGB565 pixels to RGB555 (as the real hardware does)
        a[..., 0] = ((self._screen & 0xF800) >> 11).astype(np.uint8)
        a[..., 1] = ((self._screen & 0x07E0) >> 6).astype(np.uint8)
        a[..., 2] = (self._screen & 0x001F).astype(np.uint8)
        # map all values according to the gamma table
        a = np.take(self._gamma, a)
        a = np.take(self._gamma_rgbled, a)
        return a

    @property
    def timestamp(self):
        return os.fstat(self._fd.fileno()).st_mtime

