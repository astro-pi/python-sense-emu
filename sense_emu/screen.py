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


class ScreenClient(object):
    def __init__(self):
        try:
            self._fd = io.open(screen_filename(), 'rb+')
        except IOError as e:
            # If the screen's device file doesn't exist, create it
            if e.errno == errno.ENOENT:
                self._fd = io.open(screen_filename(), 'wb+')
            else:
                raise
        # Ensure the file has 128-bytes (64 2-byte integers)
        self._fd.seek(128)
        self._fd.truncate()
        self._fd.seek(0)
        self._map = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_READ)
        self._array = np.frombuffer(self._map, dtype=np.uint16).reshape((8, 8))

    def close(self):
        if self._fd:
            self._map.close()
            self._map = None
            self._fd.close()
            self._fd = None

    @property
    def array(self):
        return self._array

    @property
    def rgb_array(self):
            a = np.empty((8, 8, 3), dtype=np.uint8)
            a[..., 0] = ((self._array & 0xF800) >> 8).astype(np.uint8)
            a[..., 1] = ((self._array & 0x07E0) >> 3).astype(np.uint8)
            a[..., 2] = ((self._array & 0x001F) << 3).astype(np.uint8)
            a[..., 0] |= a[..., 0] >> 5
            a[..., 1] |= a[..., 1] >> 6
            a[..., 2] |= a[..., 2] >> 5
            return a

