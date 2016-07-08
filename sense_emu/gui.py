from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )
str = type('')


import atexit

import pkg_resources
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


def main():
    atexit.register(pkg_resources.cleanup_resources)
    builder = Gtk.Builder()
    builder.add_from_string(pkg_resources.resource_string(__name__, 'gui.glade'))
    window = builder.get_object('window1')
    window.show_all()
    window.connect('delete-event', Gtk.main_quit)
    Gtk.main()
