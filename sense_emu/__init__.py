# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Raspberry Pi Sense HAT Emulator library for the Raspberry Pi
# Copyright (c) 2016 Raspberry Pi Foundation <info@raspberrypi.org>
#
# All Rights Reserved.

"The Raspberry Pi Sense HAT Emulator library"

from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )

import sys

from .sense_hat import SenseHat, SenseHat as AstroPi
from .stick import (
    SenseStick,
    DIRECTION_UP,
    DIRECTION_DOWN,
    DIRECTION_LEFT,
    DIRECTION_RIGHT,
    DIRECTION_MIDDLE,
    ACTION_PRESSED,
    ACTION_RELEASED,
    ACTION_HELD,
    )

__project__      = 'sense-emu'
__version__      = '0.1'
__author__       = 'Raspberry Pi Foundation'
__author_email__ = 'info@raspberrypi.org'
__url__          = 'http://sense-emu.readthedocs.io/'
__platforms__    = 'ALL'

__classifiers__ = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Environment :: X11 Applications',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: POSIX :: Linux',
    'Operating System :: Microsoft :: Windows',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.2',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    ]

__keywords__ = [
    'raspberrypi', 'sense', 'hat'
    ]

__requires__ = [
    'numpy', 'Pillow',
    ]

__extra_requires__ = {
    'doc':   ['sphinx'],
    'test':  ['pytest', 'coverage', 'mock'],
    }

if sys.version_info[:2] == (3, 2):
    # Particular versions are required for Python 3.2 compatibility
    __extra_requires__['doc'].extend([
        'Jinja2<2.7',
        'MarkupSafe<0.16',
        ])
    __extra_requires__['test'][1] = 'coverage<4.0dev'

__entry_points__ = {
    'console_scripts': [
        'sense_rec = sense_emu.record:app',
        'sense_play = sense_emu.play:app',
        ],
    'gui_scripts': [
        'sense_emu_gui = sense_emu.gui:main',
        ],
    }


