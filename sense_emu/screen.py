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
import struct


def screen_filename():
    # returns the file used to represent the state of the emulated sense HAT's
    # screen. On UNIX we try /dev/shm then fall back to /tmp; on Windows we
    # use whatever %TEMP% points at
    fname = 'rpi-sense-emu-screen'
    if sys.platform.startswith('win'):
        # just use a temporary file on Windows
        return os.join(os.environ['TEMP'], fname)
    else:
        if os.path.exists('/dev/shm'):
            return os.join('/dev/shm', fname)
        else:
            return os.join('/tmp', fname)


class ScreenClient(object):
    def __init__(self):
        self._fd = io.open(screen_filename(), 'rb')
        self._map = mmap.mmap(self._fd.fileno(), 128, access=mmap.ACCESS_READ)

    def __getitem__(self, index):
        pass

