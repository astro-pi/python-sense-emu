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

_TRANSLATIONS = None

if sys.version_info.major == 3:
    def gettext(message):
        return _TRANSLATIONS.gettext(message)

    def ngettext(singular, plural, n):
        return _TRANSLATIONS.ngettext(singular, plural, n)
else:
    def gettext(message):
        return _TRANSLATIONS.ugettext(message)
    def ngettext(singular, plural, n):
        return _TRANSLATIONS.ungettext(singular, plural, n)
_ = gettext

def init_i18n(languages=None):
    # Use the user's default locale instead of C
    locale.setlocale(locale.LC_ALL, '')
    # Ensure any resources we extract get cleaned up interpreter shutdown
    atexit.register(pkg_resources.cleanup_resources)
    # Construct a global Translations instance which we can use for _
    global _TRANSLATIONS
    _TRANSLATIONS = _gettext.translation(
        __project__, pkg_resources.resource_filename(__name__, 'translations'),
        languages, fallback=True)

