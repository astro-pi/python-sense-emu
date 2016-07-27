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
import time
import errno
import subprocess
from struct import Struct
from collections import namedtuple
from threading import Thread, Event

from .common import clamp
from .vector import Vector, X, Y, Z, O


IMU_DATA = Struct(
    '@'   # native mode
    'B'   # IMU sensor type
    '20p' # IMU sensor name
    'Q'   # timestamp
    'hhh' # OUT_X_G, OUT_Y_G, OUT_Z_G
    'hhh' # OUT_X_XL, OUT_Y_XL, OUT_Z_XL
    'hhh' # OUT_X_M, OUT_Y_M, OUT_Z_M
    )

IMUData = namedtuple('IMUData', ('type', 'name', 'timestamp', 'accel', 'gyro', 'compass'))


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


# Find the best available time-source for the timestamp() function. The best
# source will preferably be monotonic, and high-resolution
try:
    clock = time.monotonic # 3.3+ (only guaranteed in 3.5+)
except AttributeError:
    try:
        clock = time.perf_counter # 3.3+
    except AttributeError:
        clock = time.clock # fallback for 2.7
def timestamp():
    """
    Returns a timestamp as an integer number of microseconds after some
    arbitrary basis (only comparisons of consecutive calls are meaningful).
    """
    return int(clock() * 1000000)


class IMUServer(object):
    def __init__(self, simulate_world=True):
        self._fd = init_imu()
        self._map = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_WRITE)
        data = self._read()
        self._gravity = Vector(0, 0, 1)
        self._north = Vector(0, 1, 0)
        if data.type != 6:
            self._write(IMUData(6, b'LSM9DS1', timestamp(), O, O, O))
            self._accel = O
            self._gyro = O
            self._compass = O
            self._orientation = O
            self._position = O
        else:
            self._accel = data.accel / 4081.6327
            self._gyro = data.gyro / 57.142857
            self._compass = data.compass / 7142.8571
            self._orientation = O # XXX calc orientation from accel and gravity
            self._position = O # XXX calc position from compass and north
        self._world_thread = None
        self._world_event = Event()
        self._world_write()
        self.simulate_world = simulate_world

    def close(self):
        if self._fd:
            self.simulate_world = False
            self._map.close()
            self._fd.close()
            self._fd = None
            self._map = None

    def _read(self):
        (
            type, name, timestamp,
            ax, ay, az,
            gx, gy, gz,
            cx, cy, cz
            ) = IMU_DATA.unpack_from(self._map)
        return IMUData(
            type, name, timestamp,
            Vector(ax, ay, az),
            Vector(gx, gy, gz),
            Vector(cx, cy, cz)
            )

    def _write(self, value):
        value = (
            value.type, value.name, timestamp(),
            value.accel.x, value.accel.y, value.accel.z,
            value.gyro.x, value.gyro.y, value.gyro.z,
            value.compass.x, value.compass.y, value.compass.z,
            )
        IMU_DATA.pack_into(self._map, 0, *value)

    def set_orientation(self, orientation, position):
        assert self.simulate_world
        self._orientation = orientation
        self._position = position

    def set_imu_values(self, accel, gyro, compass):
        assert not self.simulate_world
        self._accel = accel
        self._gyro = gyro
        self._compass = compass
        self._world_write()

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
    def position(self):
        return self._position

    @property
    def simulate_world(self):
        return self._world_thread is not None

    @simulate_world.setter
    def simulate_world(self, value):
        if value and not self._world_thread:
            self._world_event.clear()
            self._world_thread = Thread(target=self._world_loop)
            self._world_thread.daemon = True
            self._world_thread.start()
        elif self._world_thread and not value:
            self._world_event.set()
            self._world_thread.join()
            self._world_thread = None
            self._world_write()

    def _world_loop(self):
        while True:
            old_position = self._position
            old_orientation = self._orientation
            if self._world_event.wait(0.016):
                break
            self._gyro = self._orientation - old_orientation
            xp = X.rotate(self._orientation.z, about=Z)
            yp = Y.rotate(self._orientation.z, about=Z)
            zp = Z
            xpp = xp
            ypp = yp.rotate(self._orientation.x, about=xp)
            zpp = zp.rotate(self._orientation.x, about=xp)
            xf = xpp.rotate(self._orientation.y, about=ypp)
            yf = ypp
            zf = zpp.rotate(self._orientation.y, about=zpp)
            self._accel = Vector(
                xf.dot(self._gravity),
                yf.dot(self._gravity),
                zf.dot(self._gravity),
                )
            # XXX Simulate acceleration from position
            self._world_write()

    def _world_write(self):
        self._write(self._read()._replace(
            accel=Vector(
                int(clamp(self.accel.x, -8, 8) * 4081.6327),
                int(clamp(self.accel.y, -8, 8) * 4081.6327),
                int(clamp(self.accel.z, -8, 8) * 4081.6327),
                ),
            gyro=Vector(
                int(clamp(self.gyro.x, -500, 500) * 57.142857),
                int(clamp(self.gyro.y, -500, 500) * 57.142857),
                int(clamp(self.gyro.z, -500, 500) * 57.142857),
                ),
            compass=Vector(
                int(clamp(self.compass.x, -4, 4) * 7142.8571),
                int(clamp(self.compass.y, -4, 4) * 7142.8571),
                int(clamp(self.compass.z, -4, 4) * 7142.8571),
                )
            ))

