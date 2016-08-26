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
import mmap
import errno
from struct import Struct
from collections import namedtuple
from random import Random
from time import time
from threading import Thread, Event
from math import isnan

import numpy as np

from .common import clamp


# See LPS25H data-sheet for details of register values
PRESSURE_FACTOR = 4096
TEMP_OFFSET = 37
TEMP_FACTOR = 480
PRESSURE_DATA = Struct(nstr(
    '@'   # native mode
    'B'   # pressure sensor type
    '6p'  # pressure sensor name
    'l'   # P_REF
    'l'   # P_OUT
    'h'   # T_OUT
    'B'   # P_VALID
    'B'   # T_VALID
    ))

PressureData = namedtuple('PressureData',
    ('type', 'name', 'P_REF', 'P_OUT', 'T_OUT', 'P_VALID', 'T_VALID'))


def pressure_filename():
    """
    Return the filename used to represent the state of the emulated sense HAT's
    pressure sensor. On UNIX we try ``/dev/shm`` then fall back to ``/tmp``; on
    Windows we use whatever ``%TEMP%`` contains
    """
    fname = 'rpi-sense-emu-pressure'
    if sys.platform.startswith('win'):
        # just use a temporary file on Windows
        return os.path.join(os.environ['TEMP'], fname)
    else:
        if os.path.exists('/dev/shm'):
            return os.path.join('/dev/shm', fname)
        else:
            return os.path.join('/tmp', fname)


def init_pressure():
    """
    Opens the file representing the state of the pressure sensors. The
    file-like object is returned.

    If the file already exists we simply make sure it is the right size. If
    the file does not already exist, it is created and zeroed.
    """
    try:
        # Attempt to open the IMU's device file and ensure it's the right size
        fd = io.open(pressure_filename(), 'r+b', buffering=0)
        fd.seek(PRESSURE_DATA.size)
        fd.truncate()
    except IOError as e:
        # If the screen's device file doesn't exist, create it with reasonable
        # initial values
        if e.errno == errno.ENOENT:
            fd = io.open(pressure_filename(), 'w+b', buffering=0)
            fd.write(b'\x00' * PRESSURE_DATA.size)
        else:
            raise
    return fd


class PressureServer(object):
    def __init__(self, simulate_noise=True):
        self._random = Random()
        self._fd = init_pressure()
        self._map = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_WRITE)
        data = self._read()
        if data.type != 3:
            self._write(PressureData(3, b'LPS25H', 0, 0, 0, 0, 0))
            self._pressure = 1013.0
            self._temperature = 20.0
        else:
            self._pressure = data.P_OUT / 4096
            self._temperature = data.T_OUT / 480 + 42.5
        self._noise_thread = None
        self._noise_event = Event()
        self._noise_write()
        # The queue lengths are selected to accurately represent the response
        # time of the sensors
        self._pressures = np.full((25,), self._pressure, dtype=np.float)
        self._temperatures = np.full((25,), self._temperature, dtype=np.float)
        self.simulate_noise = simulate_noise

    def close(self):
        if self._fd:
            self.simulate_noise = False
            self._map.close()
            self._fd.close()
            self._fd = None
            self._map = None

    def _perturb(self, value, error):
        """
        Return *value* perturbed by +/- *error* which is derived from a
        gaussian random generator.
        """
        # We use an internal Random() instance here to avoid a threading issue
        # with the gaussian generator (could use locks, but an instance of
        # Random is easier and faster)
        return value + self._random.gauss(0, 0.2) * error

    def _read(self):
        return PressureData(*PRESSURE_DATA.unpack_from(self._map))

    def _write(self, value):
        PRESSURE_DATA.pack_into(self._map, 0, *value)

    @property
    def pressure(self):
        return self._pressure

    @property
    def temperature(self):
        return self._temperature

    def set_values(self, pressure, temperature):
        self._pressure = pressure
        self._temperature = temperature
        if not self._noise_thread:
            self._noise_write()

    @property
    def simulate_noise(self):
        return self._noise_thread is not None

    @simulate_noise.setter
    def simulate_noise(self, value):
        if value and not self._noise_thread:
            self._noise_event.clear()
            self._noise_thread = Thread(target=self._noise_loop)
            self._noise_thread.daemon = True
            self._noise_thread.start()
        elif self._noise_thread and not value:
            self._noise_event.set()
            self._noise_thread.join()
            self._noise_thread = None
            self._noise_write()

    def _noise_loop(self):
        while not self._noise_event.wait(0.04):
            self._noise_write()

    def _noise_write(self):
        if self.simulate_noise:
            self._pressures[1:] = self._pressures[:-1]
            self._pressures[0] = self._perturb(self.pressure, (
                0.2 if 800 <= self.pressure <= 1100 and 20 <= self.temperature <= 60 else
                1.0))
            self._temperatures[1:] = self._temperatures[:-1]
            self._temperatures[0] = self._perturb(self.temperature, (
                2.0 if 0 <= self.temperature <= 65 else
                4.0))
            pressure = self._pressures.mean()
            temperature = self._temperatures.mean()
        else:
            pressure = self.pressure
            temperature = self.temperature
        self._write(self._read()._replace(
            P_VALID=not isnan(pressure),
            T_VALID=not isnan(temperature),
            P_OUT=0 if isnan(pressure) else int(clamp(pressure, 260, 1260) * PRESSURE_FACTOR),
            T_OUT=0 if isnan(temperature) else int((clamp(temperature, -30, 105) - TEMP_OFFSET) * TEMP_FACTOR),
            ))


