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
str = type('')

import os
import logging
import argparse
from threading import Thread, Event
from time import time, sleep
from struct import Struct

from . import __version__
from .terminal import TerminalApplication
from .common import HEADER_REC, DATA_REC


class RecordApplication(TerminalApplication):
    """
    Records the readings from a Raspberry Pi Sense HAT in real time, outputting
    the results to the specified file.
    """

    def __init__(self):
        super(RecordApplication, self).__init__(__version__)
        self.parser.add_argument(
            '-c', '--config', dest='config', action='store', default='/etc/RTIMULib.ini',
            help='the Sense HAT configuration file to use (default: %(default)s)')
        self.parser.add_argument('output', type=argparse.FileType('wb'))

    def main(self, args):
        try:
            import RTIMU
        except ImportError:
            raise IOError(
                'unable to import RTIMU; ensure the Sense HAT library is '
                'correctly installed')
        if not args.config.endswith('.ini'):
            raise argparse.ArgumentError('configuration filename must end with .ini')

        logging.info('Reading settings from %s', args.config)
        settings = RTIMU.Settings(args.config[:-4])
        logging.info('Initializing sensors')
        imu = RTIMU.RTIMU(settings)
        if not imu.IMUInit():
            raise IOError('Failed to initialize Sense HAT IMU')
        psensor = RTIMU.RTPressure(settings)
        if not psensor.pressureInit():
            raise IOError('Failed to initialize Sense HAT pressure sensor')
        hsensor = RTIMU.RTHumidity(settings)
        if not hsensor.humidityInit():
            raise IOError('Failed to initialize Sense HAT humidity sensor')
        interval = imu.IMUGetPollInterval() / 1000.0 # seconds
        nan = float('nan')

        logging.info('Starting output')
        rec_count = 0
        args.output.write(HEADER_REC.pack(b'SENSEHAT', 1, time()))
        status_stop = Event()
        def status():
            while not status_stop.wait(1.0):
                logging.info('%d records written', rec_count)
        status_thread = Thread(target=status)
        status_thread.daemon = True
        status_thread.start()
        try:
            while True:
                timestamp = time()
                if imu.IMURead():
                    ax, ay, az = imu.getAccel()
                    gx, gy, gz = imu.getGyro()
                    cx, cy, cz = imu.getCompass()
                    ox, oy, oz = imu.getFusionData()
                    pvalid, pressure, ptvalid, ptemp = psensor.pressureRead()
                    hvalid, humidity, htvalid, htemp = hsensor.humidityRead()
                    args.output.write(DATA_REC.pack(
                        timestamp,
                        pressure if pvalid else nan,
                        ptemp if ptvalid else nan,
                        humidity if hvalid else nan,
                        htemp if htvalid else nan,
                        ax, ay, az,
                        gx, gy, gz,
                        cx, cy, cz,
                        ox, oy, oz,
                        ))
                    rec_count += 1
                delay = max(0.0, timestamp + interval - time())
                if delay:
                    sleep(delay)
        finally:
            status_stop.set()
            status_thread.join()
            logging.info('Closing output after %d records', rec_count)
            args.output.close()


app = RecordApplication()
