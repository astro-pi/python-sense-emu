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
import datetime as dt
from time import time, sleep
from struct import Struct

from . import __version__
from .i18n import _
from .terminal import TerminalApplication, FileType
from .common import HEADER_REC, DATA_REC, DataRecord
from .imu import IMUServer
from .pressure import PressureServer
from .humidity import HumidityServer
from .lock import EmulatorLock


class PlayApplication(TerminalApplication):
    def __init__(self):
        super(PlayApplication, self).__init__(
            version=__version__,
            description=_("Replays readings recorded from a Raspberry Pi "
                "Sense HAT, via the Sense HAT emulation library."))
        self.parser.add_argument('input', type=FileType('rb'))

    def source(self, f):
        logging.info(_('Reading header'))
        magic, ver, offset = HEADER_REC.unpack(f.read(HEADER_REC.size))
        if magic != b'SENSEHAT':
            raise IOError(_('Invalid magic number at start of input'))
        if ver != 1:
            raise IOError(_('Unrecognized file version number (%d)') % ver)
        logging.info(
            _('Playing back recording taken at %s'),
            dt.datetime.fromtimestamp(offset).strftime('%c'))
        offset = time() - offset
        while True:
            buf = f.read(DATA_REC.size)
            if not buf:
                break
            elif len(buf) < DATA_REC.size:
                raise IOError(_('Incomplete data record at end of file'))
            else:
                data = DataRecord(*DATA_REC.unpack(buf))
                yield data._replace(timestamp=data.timestamp + offset)

    def main(self, args):
        lock = EmulatorLock('sense_play')
        try:
            lock.acquire()
        except:
            logging.error(
                'Another process is currently acting as the Sense HAT '
                'emulator')
            return 1
        try:
            imu = IMUServer(simulate_world=False)
            psensor = PressureServer(simulate_noise=False)
            hsensor = HumidityServer(simulate_noise=False)
            skipped = 0
            for rec, data in enumerate(self.source(args.input)):
                now = time()
                if data.timestamp < now:
                    if not skipped:
                        logging.warning(_('Skipping records to catch up'))
                    skipped += 1
                    continue
                else:
                    sleep(data.timestamp - now)
                psensor.set_values(data.pressure, data.ptemp)
                hsensor.set_values(data.humidity, data.htemp)
                imu.set_imu_values(
                    (data.ax, data.ay, data.az),
                    (data.gx, data.gy, data.gz),
                    (data.cx, data.cy, data.cz),
                    (data.ox, data.oy, data.oz),
                    )
            if skipped:
                logging.warning(_('Skipped %d records during playback'), skipped)
            logging.info(_('Finished playback of %d records'), rec)
        finally:
            lock.release()


app = PlayApplication()
