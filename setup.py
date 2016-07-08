#!/usr/bin/env python3

"""An emulator for the Raspberry Pi Sense HAT."""

import os
import sys
from setuptools import setup, find_packages

if sys.version_info[0] == 2:
    if not sys.version_info >= (2, 7):
        raise ValueError('This package requires Python 2.7 or newer')
elif sys.version_info[0] == 3:
    if not sys.version_info >= (3, 2):
        raise ValueError('This package requires Python 3.2 or newer')
else:
    raise ValueError('Unrecognized major version of Python')

HERE = os.path.abspath(os.path.dirname(__file__))

# Workaround <http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html>
try:
    import multiprocessing
except ImportError:
    pass

__project__      = 'sense_emu'
__version__      = '0.1'
__author__       = 'Dave Jones'
__author_email__ = 'dave@waveform.org.uk'
__url__          = 'http://sense_emu.readthedocs.io/'
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
    'gui_scripts': [
        'sense_emu_gui = sense_emu.gui:main',
        ],
    }


def main():
    import io
    with io.open(os.path.join(HERE, 'README.rst'), 'r') as readme:
        setup(
            name                 = __project__,
            version              = __version__,
            description          = __doc__,
            long_description     = readme.read(),
            classifiers          = __classifiers__,
            author               = __author__,
            author_email         = __author_email__,
            url                  = __url__,
            license              = [
                c.rsplit('::', 1)[1].strip()
                for c in __classifiers__
                if c.startswith('License ::')
                ][0],
            keywords             = __keywords__,
            packages             = find_packages(),
            include_package_data = True,
            platforms            = __platforms__,
            install_requires     = __requires__,
            extras_require       = __extra_requires__,
            entry_points         = __entry_points__,
            )


if __name__ == '__main__':
    main()

