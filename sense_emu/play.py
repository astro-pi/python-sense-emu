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
import datetime as dt
from threading import Thread, Event
from time import time, sleep
from struct import Struct

from . import __version__
from .terminal import TerminalApplication
from .common import HEADER_REC, DATA_REC, DataRecord
from .imu import IMUServer
from .pressure import PressureServer
from .humidity import HumidityServer


class PlayApplication(TerminalApplication):
    """
    Replays readings recorded from a Raspberry Pi Sense HAT, via the
    Sense HAT emulation library.
    """

    def __init__(self):
        super(PlayApplication, self).__init__(__version__)
        self.parser.add_argument('input', type=argparse.FileType('rb'))

    def source(self, f):
        logging.info('Reading header')
        magic, ver, offset = HEADER_REC.unpack(f.read(HEADER_REC.size))
        if magic != b'SENSEHAT':
            raise IOError('Invalid magic number at start of input')
        if ver != 1:
            raise IOError('Unrecognized file version number (%d)' % ver)
        logging.info(
            'Playing back recording taken at %s',
            dt.datetime.fromtimestamp(offset).strftime('%Y-%m-%d %H:%M:%S'))
        offset = time() - offset
        while True:
            buf = f.read(DATA_REC.size)
            if not buf:
                break
            elif len(buf) < DATA_REC.size:
                raise IOError('Incomplete data record at end of file')
            else:
                data = DataRecord(*DATA_REC.unpack(buf))
                yield data._replace(timestamp=data.timestamp + offset)

    def main(self, args):
        imu = IMUServer(simulate_world=False)
        psensor = PressureServer(simulate_noise=False)
        hsensor = HumidityServer(simulate_noise=False)
        for rec, data in enumerate(self.source(args.input)):
            now = time()
            if data.timestamp < now:
                logging.warning('Skipping record %d to catch up', rec)
            else:
                sleep(now - data.timestamp)
            psensor.set_values(data.pressure, data.ptemp)
            hsensor.set_values(data.humidity, data.htemp)
            imu.set_imu_values(
                (data.ax, data.ay, data.az),
                (data.gx, data.gy, data.gz),
                (data.cx, data.cy, data.cz),
                (data.ox, data.oy, data.oz),
                )
        logging.info('Finished playback')


app = PlayApplication()
