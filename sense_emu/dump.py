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


import sys
import os
import csv
import logging
import argparse
import datetime as dt
from time import time, sleep
from struct import Struct

from . import __version__
from .i18n import _
from .terminal import TerminalApplication, FileType
from .common import HEADER_REC, DATA_REC, DataRecord


class DumpApplication(TerminalApplication):
    def __init__(self):
        super(DumpApplication, self).__init__(
            version=__version__,
            description=_("Converts a Sense HAT recording to CSV format, for "
                "the purposes of debugging or analysis."))
        self.parser.add_argument(
            '--timestamp-format', action='store', default='%Y-%m-%dT%H:%M:%S.%f', metavar='FMT',
            help=_('the format to use when outputting the record timestamp '
            '(default: %(default)s)'))
        self.parser.add_argument(
            '--header', action='store_true', default=False,
            help=_('if specified, output column headers'))
        self.parser.add_argument('input', type=FileType('rb'))
        # Eurgh ... csv module under Python 2 only outputs byte-strings
        if sys.version_info.major == 2:
            self.parser.add_argument('output', type=FileType('wb'))
        else:
            self.parser.add_argument('output', type=FileType('w', encoding='utf-8'))

    def source(self, f):
        logging.info(_('Reading header'))
        magic, ver, offset = HEADER_REC.unpack(f.read(HEADER_REC.size))
        if magic != b'SENSEHAT':
            raise IOError(_('Invalid magic number at start of input'))
        if ver != 1:
            raise IOError(_('Unrecognized file version number (%d)') % ver)
        logging.info(
            _('Dumping recording taken at %s'),
            dt.datetime.fromtimestamp(offset).strftime('%c'))
        offset = time() - offset
        while True:
            buf = f.read(DATA_REC.size)
            if not buf:
                break
            elif len(buf) < DATA_REC.size:
                raise IOError(_('Incomplete data record at end of file'))
            else:
                yield DataRecord(*DATA_REC.unpack(buf))

    def main(self, args):
        writer = csv.writer(args.output)
        if args.header:
            writer.writerow((
                'timestamp',
                'pressure', 'pressure_temp',
                'humidity', 'humidity_temp',
                'accel_x', 'accel_y', 'accel_z',
                'gyro_x', 'gyro_y', 'gyro_z',
                'compass_x', 'compass_y', 'compass_z',
                'orient_x', 'orient_y', 'orient_z',
                ))
        for rec, data in enumerate(self.source(args.input)):
            writer.writerow((
                dt.datetime.fromtimestamp(data.timestamp).strftime(args.timestamp_format),
                data.pressure, data.ptemp,
                data.humidity, data.htemp,
                data.ax, data.ay, data.az,
                data.gx, data.gy, data.gz,
                data.cx, data.cy, data.cz,
                data.ox, data.oy, data.oz,
                ))
        logging.info(_('Converted %d records'), rec)


app = DumpApplication()
