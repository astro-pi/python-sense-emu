# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Raspberry Pi Sense HAT Emulator library for the Raspberry Pi
# Copyright (c) 2016 Raspberry Pi Foundation <info@raspberrypi.org>
#
# This package is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This package is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>


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
from .i18n import _
from .terminal import TerminalApplication, FileType
from .common import HEADER_REC, DATA_REC


class RecordApplication(TerminalApplication):
    def __init__(self):
        super(RecordApplication, self).__init__(
            version=__version__,
            description=_("Records the readings from a Raspberry Pi Sense HAT "
                "in real time, outputting the results to the specified file."))
        self.parser.add_argument(
            '-c', '--config', dest='config', action='store',
            default='/etc/RTIMULib.ini', metavar='FILE',
            help=_('the Sense HAT configuration file to use (default: %(default)s)'))
        self.parser.add_argument(
            '-d', '--duration', dest='duration', action='store', default=0.0,
            type=float, metavar='SECS',
            help=_('the duration to record for in seconds (default: record '
            'until terminated with Ctrl+C)'))
        self.parser.add_argument(
            '-i', '--interval', dest='interval', action='store',
            type=float, metavar='SECS',
            help=_('the delay between each reading in seconds (default: the '
                   'IMU polling interval, typically 0.003 seconds)'))
        self.parser.add_argument(
            '-f', '--flush', dest='flush', action='store_true', default=False,
            help=_('flush every record to disk immediately; reduces chances of '
            'truncated data on power loss, but greatly increases disk activity'))
        self.parser.add_argument('output', type=FileType('wb'))

    def main(self, args):
        try:
            import RTIMU
        except ImportError:
            raise IOError(
                _('unable to import RTIMU; ensure the Sense HAT library is '
                'correctly installed'))
        if not args.config.endswith('.ini'):
            raise argparse.ArgumentError(_('configuration filename must end with .ini'))

        logging.info(_('Reading settings from %s'), args.config)
        settings = RTIMU.Settings(args.config[:-4])
        logging.info(_('Initializing sensors'))
        imu = RTIMU.RTIMU(settings)
        if not imu.IMUInit():
            raise IOError(_('Failed to initialize Sense HAT IMU'))
        psensor = RTIMU.RTPressure(settings)
        if not psensor.pressureInit():
            raise IOError(_('Failed to initialize Sense HAT pressure sensor'))
        hsensor = RTIMU.RTHumidity(settings)
        if not hsensor.humidityInit():
            raise IOError(_('Failed to initialize Sense HAT humidity sensor'))
        if args.interval is None:
            args.interval = imu.IMUGetPollInterval() / 1000.0 # seconds
        nan = float('nan')

        logging.info(_('Starting recording'))
        rec_count = 0
        if args.duration:
            terminate_at = time() + args.duration
        else:
            terminate_at = time() + 1e100
        args.output.write(HEADER_REC.pack(b'SENSEHAT', 1, time()))
        status_stop = Event()
        def status():
            while not status_stop.wait(1.0):
                logging.info(_('%d records written'), rec_count)
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
                    if args.flush:
                        args.output.flush()
                    rec_count += 1
                if timestamp > terminate_at:
                    break
                delay = max(0.0, timestamp + args.interval - time())
                if delay:
                    sleep(delay)
        finally:
            status_stop.set()
            status_thread.join()
            logging.info(_('Finishing recording after %d records'), rec_count)
            args.output.close()


app = RecordApplication()
