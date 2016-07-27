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
from collections import namedtuple
from random import Random
from time import time
from threading import Thread, Lock, Event

from .common import clamp
from .vector import Vector


IMU_DATA = Struct(
    '<'   # little endian
    'B'   # IMU sensor type
    '20p' # IMU sensor name
    'hhh' # OUT_X_G, OUT_Y_G, OUT_Z_G
    'hhh' # OUT_X_XL, OUT_Y_XL, OUT_Z_XL
    'hhh' # OUT_X_M, OUT_Y_M, OUT_Z_M
    )

IMUData = namedtuple('IMUData', ('type', 'name', 'accel', 'gyro', 'compass'))


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


class IMUServer(object):
    def __init__(self, simulate_noise=True):
        self._random = Random()
        self._fd = init_imu()
        self._map = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_WRITE)
        data = self._read()
        if data.type != 6:
            self._write(IMUData(
                6, b'LSM9DS1', Vector(0, 0, 0), Vector(0, 0, 0), Vector(0, 0, 0)))
            self._accel = Vector(0.0, 0.0, 0.0)
            self._gyro = Vector(0.0, 0.0, 0.0)
            self._compass = Vector(0.0, 0.0, 0.0)
            self._orientation = Vector(0.0, 0.0, 0.0)
        else:
            self._accel = data.accel / 1000
            self._gyro = data.gyro / 1000
            self._compass = data.compass / 1000
            self._orientation = Vector(0.0, 0.0, 0.0) # XXX calc orientation from accel and gravity
        self._noise_thread = None
        self._noise_event = Event()
        self._noise_write()
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
        return Vector(
            value.x + self._random.gauss(0, 0.2) * error,
            value.y + self._random.gauss(0, 0.2) * error,
            value.z + self._random.gauss(0, 0.2) * error,
            )

    def _read(self):
        type, name, ax, ay, az, gx, gy, gz, cx, cy, cz = IMU_DATA.unpack_from(self._map)
        return IMUData(
            type, name, Vector(ax, ay, az), Vector(gx, gy, gz), Vector(cx, cy, cz))

    def _write(self, value):
        value = (
            value.type, value.name,
            value.accel.x, value.accel.y, value.accel.z,
            value.gyro.x, value.gyro.y, value.gyro.z,
            value.compass.x, value.compass.y, value.compass.z,
            )
        IMU_DATA.pack_into(self._map, 0, *value)

    def set_orientation(self, value):
        self._orientation = value
        # XXX Calculate accel, gyro, and compass from vector
        if not self._noise_thread:
            self._noise_write()

    def set_imu_values(self, accel, gyro, compass):
        self._accel = accel
        self._gyro = gyro
        self._compass = compass
        # XXX Calculate orientation from changes
        if not self._noise_thread:
            self._noise_write()

    @property
    def accel(self):
        return self._accel

    @property
    def gyro(self):
        return self._gyro

    @property
    def compass(self):
        return self._compass

    @property
    def orientation(self):
        return self._orientation

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
        while not self._noise_event.wait(0.016):
            self._noise_write()

    def _noise_write(self):
        if self.simulate_noise:
            accel = self._perturb(self.accel, 0.244 / 1000)
            gyro = self._perturb(self.gyro, 17.50 / 1000)
            compass = self._perturb(self.compass, 0.14 / 1000)
        else:
            accel = self.accel
            gyro = self.gyro
            compass = self.compass
        self._write(self._read()._replace(
            accel=Vector(
                int(clamp(accel.x, -8, 8) * 1000),
                int(clamp(accel.y, -8, 8) * 1000),
                int(clamp(accel.z, -8, 8) * 1000),
                ),
            gyro=Vector(
                int(clamp(gyro.x, -500, 500) * 1000),
                int(clamp(gyro.y, -500, 500) * 1000),
                int(clamp(gyro.z, -500, 500) * 1000),
                ),
            compass=Vector(
                int(clamp(compass.x, -4, 4) * 1000),
                int(clamp(compass.y, -4, 4) * 1000),
                int(clamp(compass.z, -4, 4) * 1000),
                )
            ))

