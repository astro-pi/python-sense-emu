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


# See HTS221 data-sheet for details of register values
HUMIDITY_FACTOR = 256
TEMP_FACTOR = 64
HUMIDITY_DATA = Struct(
    '@'   # native mode
    'B'   # humidity sensor type
    '6p'  # humidity sensor name
    'B'   # H0
    'B'   # H1
    'H'   # T0
    'H'   # T1
    'h'   # H0_OUT
    'h'   # H1_OUT
    'h'   # T0_OUT
    'h'   # T1_OUT
    'h'   # H_OUT
    'h'   # T_OUT
    'B'   # H_VALID
    'B'   # T_VALID
)

HumidityData = namedtuple('HumidityData', (
    'type', 'name', 'H0', 'H1', 'T0', 'T1', 'H0_OUT', 'H1_OUT',
    'T0_OUT', 'T1_OUT', 'H_OUT', 'T_OUT', 'H_VALID', 'T_VALID')
)


def humidity_filename():
    """
    Return the filename used to represent the state of the emulated sense HAT's
    humidity sensor. On UNIX we try ``/dev/shm`` then fall back to ``/tmp``; on
    Windows we use whatever ``%TEMP%`` contains
    """
    fname = 'rpi-sense-emu-humidity'
    if sys.platform.startswith('win'):
        # just use a temporary file on Windows
        return os.path.join(os.environ['TEMP'], fname)
    else:
        if os.path.exists('/dev/shm'):
            return os.path.join('/dev/shm', fname)
        else:
            return os.path.join('/tmp', fname)


def init_humidity():
    """
    Opens the file representing the state of the humidity sensor. The
    file-like object is returned.

    If the file already exists we simply make sure it is the right size. If
    the file does not already exist, it is created and zeroed.
    """
    try:
        # Attempt to open the humidity sensor's file and ensure it's the right
        # size
        fd = io.open(humidity_filename(), 'r+b', buffering=0)
        fd.seek(HUMIDITY_DATA.size)
        fd.truncate()
    except IOError as e:
        # If the humidity device's file doesn't exist, create it with
        # reasonable initial values
        if e.errno == errno.ENOENT:
            fd = io.open(humidity_filename(), 'w+b', buffering=0)
            fd.write(b'\x00' * HUMIDITY_DATA.size)
        else:
            raise
    return fd


class HumidityServer:
    def __init__(self, simulate_noise=True):
        self._random = Random()
        self._fd = init_humidity()
        self._map = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_WRITE)
        data = self._read()
        if data.type != 2:
            self._write(HumidityData(2, b'HTS221', 0, 100, 0, 100, 0, 25600, 0, 6400, 0, 0, 0, 0))
            self._humidity = 45.0
            self._temperature = 20.0
        else:
            self._humidity = data.H_OUT / HUMIDITY_FACTOR
            self._temperature = data.T_OUT / TEMP_FACTOR
        self._noise_thread = None
        self._noise_event = Event()
        self._noise_write()
        # The queue lengths are selected to accurately represent the response
        # time of the sensors
        self._humidities = np.full((10,), self._humidity, dtype=float)
        self._temperatures = np.full((31,), self._temperature, dtype=float)
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
        return HumidityData(*HUMIDITY_DATA.unpack_from(self._map))

    def _write(self, value):
        HUMIDITY_DATA.pack_into(self._map, 0, *value)

    @property
    def humidity(self):
        return self._humidity

    @property
    def temperature(self):
        return self._temperature

    def set_values(self, humidity, temperature):
        self._humidity = humidity
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
        while not self._noise_event.wait(0.13):
            self._noise_write()

    def _noise_write(self):
        if self.simulate_noise:
            self._humidities[1:] = self._humidities[:-1]
            self._humidities[0] = self._perturb(self.humidity, (
                3.5 if 20 <= self.humidity <= 80 else
                5.0))
            self._temperatures[1:] = self._temperatures[:-1]
            self._temperatures[0] = self._perturb(self.temperature, (
                0.5 if 15 <= self.temperature <= 40 else
                1.0 if 0 <= self.temperature <= 60 else
                2.0))
            humidity = self._humidities.mean()
            temperature = self._temperatures.mean()
        else:
            humidity = self.humidity
            temperature = self.temperature
        self._write(self._read()._replace(
            H_VALID=not isnan(humidity),
            T_VALID=not isnan(temperature),
            H_OUT=0 if isnan(humidity) else int(clamp(humidity, 0, 100) * HUMIDITY_FACTOR),
            T_OUT=0 if isnan(temperature) else int(clamp(temperature, -40, 120) * TEMP_FACTOR),
            ))


