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


import mmap
from time import time

import numpy as np

from .pressure import init_pressure, PRESSURE_DATA, PressureData, PRESSURE_FACTOR, TEMP_FACTOR, TEMP_OFFSET
from .humidity import init_humidity, HUMIDITY_DATA, HumidityData
from .imu import init_imu, IMU_DATA, IMUData, ACCEL_FACTOR, GYRO_FACTOR, COMPASS_FACTOR, ORIENT_FACTOR


class Settings(object):
    def __init__(self, path):
        self.path = path


class RTIMU(object):
    def __init__(self, settings):
        self.settings = settings
        self._fd = init_imu()
        self._map = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_READ)
        self._last_data = None
        self._imu_data = {
            'accel':            (0.0, 0.0, 0.0),
            'accelValid':       False,
            'compass':          (0.0, 0.0, 0.0),
            'compassValid':     False,
            'fusionPose':       (0.0, 0.0, 0.0),
            'fusionPoseValid':  False,
            'fusionQPose':      (0.0, 0.0, 0.0, 0.0),
            'fusionQPoseValid': False,
            'gyro':             (0.0, 0.0, 0.0),
            'gyroValid':        False,
            'humidity':         float('nan'),
            'humidityValid':    False,
            'pressure':         float('nan'),
            'pressureValid':    False,
            'temperature':      float('nan'),
            'temperatureValid': False,
            'timestamp':        0,
            }

    def _read(self):
        (
            type, name, timestamp,
            ax, ay, az,
            gx, gy, gz,
            cx, cy, cz,
            ox, oy, oz,
            ) = IMU_DATA.unpack_from(self._map)
        return IMUData(
            type, name, timestamp,
            np.array((ax, ay, az)),
            np.array((gx, gy, gz)),
            np.array((cx, cy, cz)),
            np.array((ox, oy, oz)),
            )

    def IMUInit(self):
        self._last_data = self._read()
        return self._last_data.type != 0

    def IMUGetPollInterval(self):
        return 10 # 3 on the actual board

    def IMUGetGyroBiasValid(self):
        raise NotImplementedError

    def IMURead(self):
        data = self._read()
        if data.timestamp == self._last_data.timestamp:
            return False
        else:
            self._last_data = data
            self._imu_data = {
                'accel':            tuple(data.accel / ACCEL_FACTOR),
                'accelValid':       True,
                'compass':          tuple((data.compass / COMPASS_FACTOR) * 100), # convert Gauss to uT
                'compassValid':     True,
                'fusionPose':       tuple(data.orient / ORIENT_FACTOR),
                'fusionPoseValid':  True,
                'fusionQPose':      (0.0, 0.0, 0.0, 0.0),
                'fusionQPoseValid': False,
                'gyro':             tuple(data.gyro / GYRO_FACTOR),
                'gyroValid':        True,
                'humidity':         float('nan'),
                'humidityValid':    False,
                'pressure':         float('nan'),
                'pressureValid':    False,
                'temperature':      float('nan'),
                'temperatureValid': False,
                'timestamp':        data.timestamp,
                }
            return True

    def IMUType(self):
        return self._read().type # 6 in real unit

    def IMUName(self):
        return self._read().name.decode('ascii') # "LSM9DS1" in real unit

    def getAccel(self):
        return self._imu_data['accel']

    def getAccelCalibrationValid(self):
        raise NotImplementedError

    def getAccelResiduals(self):
        raise NotImplementedError

    def getCompass(self):
        return self._imu_data['compass']

    def getCompassCalibrationEllipsoidValid(self):
        raise NotImplementedError

    def getCompassCalibrationValid(self):
        raise NotImplementedError

    def getFusionData(self):
        return self._imu_data['fusionPose']

    def getGyro(self):
        return self._imu_data['gyro']

    def getIMUData(self):
        return self._imu_data

    def getMeasuredPose(self):
        raise NotImplementedError

    def getMeasuredQPose(self):
        raise NotImplementedError

    def setCompassEnable(self, value):
        pass

    def setGyroEnable(self, value):
        pass

    def setAccelEnable(self, value):
        pass


class RTPressure(object):
    def __init__(self, settings):
        self.settings = settings
        self._fd = init_pressure()
        self._map = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_READ)
        self._last_read = 0.0
        self._last_data = None
        self._p_ref = None

    def _read(self):
        now = time()
        if now - self._last_read > 0.04:
            self._last_read = now
            self._last_data = PressureData(*PRESSURE_DATA.unpack_from(self._map))
        return self._last_data

    def pressureInit(self):
        d = self._read()
        self._p_ref = d.P_REF
        return d.type != 0

    def pressureRead(self):
        if self._p_ref is None:
            return (0, 0.0, 0, 0.0)
        else:
            d = self._read()
            return (
                d.P_VALID, d.P_OUT / PRESSURE_FACTOR,
                d.T_VALID, d.T_OUT / TEMP_FACTOR + TEMP_OFFSET,
                )

    def pressureType(self):
        return self._read().type

    def pressureName(self):
        return self._read().name.decode('ascii')


class RTHumidity(object):
    def __init__(self, settings):
        self.settings = settings
        self._fd = init_humidity()
        self._map = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_READ)
        self._last_read = 0.0
        self._last_data = None
        self._humidity_m = None
        self._humidity_c = None
        self._temp_m = None
        self._temp_c = None

    def _read(self):
        now = time()
        if now - self._last_read > 0.13:
            self._last_read = now
            self._last_data = HumidityData(*HUMIDITY_DATA.unpack_from(self._map))
        return self._last_data

    def humidityInit(self):
        d = self._read()
        try:
            self._humidity_m = (d.H1 - d.H0) / (d.H1_OUT - d.H0_OUT)
            self._humidity_c = d.H0 - self._humidity_m * d.H0_OUT
            self._temp_m = (d.T1 - d.T0) / (d.T1_OUT - d.T0_OUT)
            self._temp_c = d.T0 - self._temp_m * d.T0_OUT
            return True
        except ZeroDivisionError:
            return False

    def humidityRead(self):
        if self._temp_m is None:
            return (0, 0.0, 0, 0.0)
        else:
            d = self._read()
            return (
                d.H_VALID, d.H_OUT * self._humidity_m + self._humidity_c,
                d.T_VALID, d.T_OUT * self._temp_m + self._temp_c,
                )

    def humidityType(self):
        return self._read().type

    def humidityName(self):
        return self._read().name.decode('ascii')


