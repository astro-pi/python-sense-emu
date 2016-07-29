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

import numpy as np

from .common import clamp


ACCEL_FACTOR = 4081.6327
GYRO_FACTOR = 57.142857
COMPASS_FACTOR = 7142.8571
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


# Some handy array definitions
O = np.array((0, 0, 0))
X = np.array((1, 0, 0))
Y = np.array((0, 1, 0))
Z = np.array((0, 0, 1))
V = lambda x, y, z: np.array((x, y, z))


class IMUServer(object):
    def __init__(self, simulate_world=True):
        self._fd = init_imu()
        self._map = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_WRITE)
        data = self._read()
        self._gravity = Z
        self._north = X
        if data.type != 6:
            self._write(IMUData(6, b'LSM9DS1', timestamp(), O, O, O))
            self._accel = O
            self._gyro = O
            self._compass = O
            self._orientation = O
            self._position = O
        else:
            self._accel = data.accel / ACCEL_FACTOR
            self._gyro = data.gyro / GYRO_FACTOR
            self._compass = data.compass / COMPASS_FACTOR
            self._orientation = O # XXX calc orientation from accel and gravity
            self._position = O # XXX calc position from compass and north
        self._world_thread = None
        self._world_event = Event()
        self._world_write(timestamp())
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
            V(ax, ay, az),
            V(gx, gy, gz),
            V(cx, cy, cz),
            )

    def _write(self, value):
        value = (
            value.type, value.name, value.timestamp,
            value.accel[0], value.accel[1], value.accel[2],
            value.gyro[0], value.gyro[1], value.gyro[2],
            value.compass[0], value.compass[1], value.compass[2],
            )
        IMU_DATA.pack_into(self._map, 0, *value)

    def set_orientation(self, orientation, position=None):
        assert self.simulate_world
        if position is None:
            position = O
        self._orientation = V(*orientation)
        self._position = V(*position)

    def set_imu_values(self, accel, gyro, compass):
        assert not self.simulate_world
        self._accel = accel
        self._gyro = gyro
        self._compass = compass
        self._world_write(timestamp())

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
            self._world_write(timestamp())

    def _world_loop(self):
        old_timestamp = timestamp()
        old_position = self._position
        old_orientation = self._orientation
        while not self._world_event.wait(0.016):
            # Gyro reading is simply the rate of change of the orientation
            new_timestamp = timestamp()
            time_delta = new_timestamp - old_timestamp
            self._gyro = (self._orientation - old_orientation) / time_delta
            # Construct a rotation matrix for the orientation; see
            # https://en.wikipedia.org/wiki/Euler_angles#Rotation_matrix
            x, y, z = np.deg2rad(self._orientation)
            c1, c2, c3 = np.cos((z, x, y))
            s1, s2, s3 = np.sin((z, x, y))
            R = np.array([
                [c1 * c3 - s1 * s2 * s3, -c2 * s1, c1 * s3 + c3 * s1 * s2],
                [c3 * s1 + c1 * s2 * s3,  c1 * c2, s1 * s3 - c1 * c3 * s2],
                [-c2 * s3,                s2,      c2 * c3],
                ])
            self._accel = R.T.dot(self._gravity) # transpose for passive rotation
            # XXX Simulate acceleration from position
            self._world_write(new_timestamp)
            old_timestamp = new_timestamp
            old_position = self._position
            old_orientation = self._orientation

    def _world_write(self, timestamp):
        self._write(self._read()._replace(
            timestamp=timestamp,
            accel=V(
                int(clamp(self.accel[0], -8, 8) * ACCEL_FACTOR),
                int(clamp(self.accel[1], -8, 8) * ACCEL_FACTOR),
                int(clamp(self.accel[2], -8, 8) * ACCEL_FACTOR),
                ),
            gyro=V(
                int(clamp(self.gyro[0], -500, 500) * GYRO_FACTOR),
                int(clamp(self.gyro[1], -500, 500) * GYRO_FACTOR),
                int(clamp(self.gyro[2], -500, 500) * GYRO_FACTOR),
                ),
            compass=V(
                int(clamp(self.compass[0], -4, 4) * COMPASS_FACTOR),
                int(clamp(self.compass[1], -4, 4) * COMPASS_FACTOR),
                int(clamp(self.compass[2], -4, 4) * COMPASS_FACTOR),
                )
            ))

