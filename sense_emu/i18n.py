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
    # Figure out where the language catalogs are; this will extract them
    # if the package is frozen
    localedir = pkg_resources.resource_filename(__name__, 'locale')
    try:
        # Use the user's default locale instead of C
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error as e:
        # If locale is not supported, use C which should at least provide
        # consistency. In this case, don't set a gettext domain to prevent
        # translation of strings
        locale.setlocale(locale.LC_ALL, 'C')
    else:
        # Set translation domain for GNU's gettext (needed by GTK's Builder)
        try:
            locale.bindtextdomain(__project__, localedir)
            locale.textdomain(__project__)
        except AttributeError:
            if sys.platform.startswith('win'):
                try:
                    # We're on Windows; try and use intl.dll instead
                    import ctypes
                    libintl = ctypes.cdll.LoadLibrary('intl.dll')
                except OSError:
                    # intl.dll isn't available; give up
                    return
                else:
                    libintl.bindtextdomain(__project__, localedir)
                    libintl.textdomain(__project__)
                    libintl.bind_textdomain_codeset(__project, 'UTF-8')
            else:
                # We're on something else (Mac OS X most likely); no idea what
                # to do here yet
                return
        # Finally, set translation domain for Python's built-in gettext
        _gettext.bindtextdomain(__project__, localedir)
        _gettext.textdomain(__project__)


if sys.version_info.major == 3:
    gettext = _gettext.gettext
    ngettext = _gettext.ngettext
else:
    gettext = lambda message: _gettext.gettext(message).decode('utf-8')
    ngettext = lambda singular, plural, n: _gettext.ngettext(singular, plural, n).decode('utf-8')
_ = gettext

