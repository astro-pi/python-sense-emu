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
import csv
import logging
import argparse
import datetime as dt
from time import time, sleep
from struct import Struct

from . import __version__
from .terminal import TerminalApplication, FileType
from .common import HEADER_REC, DATA_REC, DataRecord


class DumpApplication(TerminalApplication):
    """
    Converts a Sense HAT recording to CSV format, for the purposes of
    debugging or analysis.
    """

    def __init__(self):
        super(DumpApplication, self).__init__(__version__)
        self.parser.add_argument(
            '--timestamp-format', action='store', default='%Y-%m-%dT%H:%M:%S',
            help='the format to use when outputting the record timestamp '
            '(default: %(default)s)')
        self.parser.add_argument(
            '--header', action='store_true', default=False,
            help='if specified, output column headers')
        self.parser.add_argument('input', type=FileType('rb'))
        self.parser.add_argument('output', type=FileType('w'))

    def source(self, f):
        logging.info('Reading header')
        magic, ver, offset = HEADER_REC.unpack(f.read(HEADER_REC.size))
        if magic != b'SENSEHAT':
            raise IOError('Invalid magic number at start of input')
        if ver != 1:
            raise IOError('Unrecognized file version number (%d)' % ver)
        logging.info(
            'Dumping recording taken at %s',
            dt.datetime.fromtimestamp(offset).strftime('%Y-%m-%d %H:%M:%S'))
        offset = time() - offset
        while True:
            buf = f.read(DATA_REC.size)
            if not buf:
                break
            elif len(buf) < DATA_REC.size:
                raise IOError('Incomplete data record at end of file')
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
        for data in self.source(args.input):
            writer.writerow((
                dt.datetime.fromtimestamp(data.timestamp).strftime(args.timestamp_format),
                data.pressure, data.ptemp,
                data.humidity, data.htemp,
                data.ax, data.ay, data.az,
                data.gx, data.gy, data.gz,
                data.cx, data.cy, data.cz,
                data.ox, data.oy, data.oz,
                ))


app = DumpApplication()
