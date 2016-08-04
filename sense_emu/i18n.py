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

import sys
import locale
import gettext as _gettext
import atexit

import pkg_resources

from . import __project__

def init_i18n(languages=None):
    # Ensure any resources we extract get cleaned up interpreter shutdown
    atexit.register(pkg_resources.cleanup_resources)
    # Set translation domain for Python's gettext
    localedir = pkg_resources.resource_filename(__name__, 'locale')
    _gettext.bindtextdomain(__project__, localedir)
    _gettext.textdomain(__project__)
    # Use the user's default locale instead of C
    locale.setlocale(locale.LC_ALL, '')
    # Now set translation domain for GNU's gettext (needed by GTK's Builder)
    locale.bindtextdomain(__project__, localedir)
    locale.textdomain(__project__)

if sys.version_info.major == 3:
    gettext = _gettext.gettext
    ngettext = _gettext.ngettext
else:
    gettext = lambda message: _gettext.gettext(message).decode('utf-8')
    ngettext = lambda singular, plural, n: _gettext.ngettext(singular, plural, n).decode('utf-8')
_ = gettext

