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
import struct
import subprocess
from collections import namedtuple
from random import random
from time import time


IMU_DATA = struct.Struct(
    '<'   # little endian
    'B'   # IMU sensor type
    '20p' # IMU sensor name
    )

HUMIDITY_DATA = struct.Struct(
    '<'   # little endian
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
    )

PRESSURE_DATA = struct.Struct(
    '<'   # little endian
    'B'   # pressure sensor type
    '6p'  # pressure sensor name
    'l'   # P_REF
    'l'   # P_OUT
    'h'   # T_OUT
    )

IMUData = namedtuple('IMUData',
    ('type', 'name', 'accel', 'gyro', 'compass'))
HumidityData = namedtuple('HumidityData',
    ('type', 'name', 'H0', 'H1', 'T0', 'T1', 'H0_OUT', 'H1_OUT', 'T0_OUT', 'T1_OUT', 'H_OUT', 'T_OUT'))
PressureData = namedtuple('PressureData',
    ('type', 'name', 'P_REF', 'P_OUT', 'T_OUT'))


clamp = lambda value, min_value, max_value: min(max_value, max(min_value, value))
perturb = lambda value, error: value + (random() * 2 - 1) * error


def imu_filename():
    # returns the file used to represent the state of the emulated sense HAT's
    # IMU, pressure and humidity sensors. On UNIX we try /dev/shm then fall
    # back to /tmp; on Windows we use whatever %TEMP% points at
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
    try:
        # Attempt to open the IMU's device file and ensure it's the right size
        fd = io.open(imu_filename(), 'r+b', buffering=0)
        fd.seek(IMU_DATA.size + HUMIDITY_DATA.size + PRESSURE_DATA.size)
        fd.truncate()
    except IOError as e:
        # If the screen's device file doesn't exist, create it with reasonable
        # initial values
        if e.errno == errno.ENOENT:
            fd = io.open(imu_filename(), 'w+b', buffering=0)
            fd.write(b'\x00' * (IMU_DATA.size + HUMIDITY_DATA.size + PRESSURE_DATA.size))
        else:
            raise
    return fd


class Settings(object):
    def __init__(self, path):
        self.path = path


class RTIMU(object):
    def __init__(self, settings):
        self._settings = settings
        self._initialized = False
        self._imu_init = {}
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

    def IMUInit(self):
        # XXX set up mmap, read IMU type and name; return True if they're
        # filled in
        return bool(self._imu_init)

    def IMUGetPollInterval(self):
        return self._imu_init['poll'] # 3 in real unit

    def IMUGetGyroBiasValid(self):
        raise NotImplementedError

    def IMURead(self):
        if self._initialized:
            # XXX copy mmap data to internal struct
            return True
        else:
            return False

    def IMUType(self):
        return self._imu_init['type'] # 6 in real unit

    def IMUName(self):
        return self._imu_init['name'] # "LSM9DS1" in real unit

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


class RTPressure(object):
    def __init__(self, settings):
        self.settings = settings
        self._fd = init_imu()
        self._map = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_READ)
        self._last_read = 0.0
        self._last_data = None
        self._p_ref = None

    def _read(self):
        now = time()
        if now - self._last_read > 0.04:
            self._last_read = now
            self._last_data = PressureData(*PRESSURE_DATA.unpack_from(self._map,
                IMU_DATA.size + HUMIDITY_DATA.size))
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
                1, d.P_OUT / 4096,
                1, d.T_OUT / 480 + 42.5,
                )

    def pressureType(self):
        return self._read().type

    def pressureName(self):
        return self._read().name.decode('ascii')


class RTHumidity(object):
    def __init__(self, settings):
        self.settings = settings
        self._fd = init_imu()
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
            self._last_data = HumidityData(
                *HUMIDITY_DATA.unpack_from(self._map, IMU_DATA.size))
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
                1, d.H_OUT * self._humidity_m + self._humidity_c,
                1, d.T_OUT * self._temp_m + self._temp_c,
                )

    def humidityType(self):
        return self._read().type

    def humidityName(self):
        return self._read().name.decode('ascii')


class PressureServer(object):
    def __init__(self, simulate_noise=True):
        self._fd = init_imu()
        self._map = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_WRITE)
        self._write(PressureData(3, b'LPS25H', 0, 0, 0))
        self._noise = simulate_noise
        self.pressure = 1000.0
        self.temperature = 25.0

    def _read(self):
        return PressureData(*PRESSURE_DATA.unpack_from(self._map,
            IMU_DATA.size + HUMIDITY_DATA.size))

    def _write(self, value):
        PRESSURE_DATA.pack_into(
            self._map, IMU_DATA.size + HUMIDITY_DATA.size, *value)

    @property
    def pressure(self):
        return clamp(self._read().P_OUT / 4096, 260, 1260)

    @pressure.setter
    def pressure(self, value):
        error = (
            0.0 if not self._noise else
            0.2 if 800 <= value <= 1100 and 20 <= self.temperature <= 60 else
            1.0)
        self._write(self._read()._replace(
            P_OUT=int(clamp(perturb(value, error), 260, 1260) * 4096)))

    @property
    def temperature(self):
        return clamp(self._read().T_OUT / 480 + 42.5, -30, 105)

    @temperature.setter
    def temperature(self, value):
        error = (
            0.0 if not self._noise else
            2.0 if 0 <= value <= 65 else
            4.0)
        self._write(self._read()._replace(
            T_OUT=int((clamp(perturb(value, error), -30, 105) - 42.5) * 480)))


class HumidityServer(object):
    def __init__(self, simulate_noise=True):
        self._fd = init_imu()
        self._map = mmap.mmap(self._fd.fileno(), 0, access=mmap.ACCESS_WRITE)
        self._write(HumidityData(2, b'HTS221', 0, 100, 0, 100, 0, 25600, 0, 6400, 0, 0))
        self._noise = simulate_noise
        self.humidity = 50.0
        self.temperature = 25.0

    def _read(self):
        return HumidityData(*HUMIDITY_DATA.unpack_from(self._map, IMU_DATA.size))

    def _write(self, value):
        HUMIDITY_DATA.pack_into(self._map, IMU_DATA.size, *value)

    @property
    def humidity(self):
        return clamp(self._read().H_OUT / 256, 0, 100)

    @humidity.setter
    def humidity(self, value):
        error = (
            0.0 if not self._noise else
            3.5 if 20 <= value <= 80 else
            5.0)
        self._write(self._read()._replace(
            H_OUT=int(clamp(perturb(value, error), 0, 100) * 256)))

    @property
    def temperature(self):
        return clamp(self._read().T_OUT / 64, -40, 120)

    @temperature.setter
    def temperature(self, value):
        error = (
            0.0 if not self._noise else
            0.5 if 15 <= value <= 40 else
            1.0 if 0 <= value <= 60 else
            2.0)
        self._write(self._read()._replace(
            T_OUT=int(clamp(perturb(value, error), -40, 120) * 64)))

