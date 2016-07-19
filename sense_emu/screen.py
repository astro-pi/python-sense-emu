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
        self._screen = np.frombuffer(self._map, dtype=np.uint16, count=64).reshape((8, 8))
        self._gamma = np.frombuffer(self._map, dtype=np.uint8, count=32, offset=128)

    def close(self):
        if self._fd:
            self._map.close()
            self._map = None
            self._fd.close()
            self._fd = None

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
        # convert to RGB888
        a = a << 3 | a >> 2
        return a

    @property
    def timestamp(self):
        return os.fstat(self._fd.fileno()).st_mtime

