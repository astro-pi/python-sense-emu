from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )
str = type('')


import sys
import atexit
from time import sleep
from threading import Thread, Lock

import numpy as np
import pkg_resources
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib, GObject

from .screen import ScreenClient


class EmuApplication(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super(EmuApplication, self).__init__(
                *args, application_id='org.raspberrypi.sense_hat_emu',
                flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                **kwargs)
        self.window = None

    def do_startup(self):
        # super-call needs to be in this form?!
        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new('about', None)
        action.connect('activate', self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new('quit', None)
        action.connect('activate', self.on_quit)
        self.add_action(action)

        builder = Gtk.Builder.new_from_string(pkg_resources.resource_string(__name__, 'app_menu.xml').decode('utf-8'), -1)
        self.set_app_menu(builder.get_object('app-menu'))

    def do_activate(self):
        if not self.window:
            self.window = EmuWindow(application=self, title='Sense HAT Emulator')
        self.window.present()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        # do stuff with switches
        self.activate()
        return 0

    def on_about(self, action, param):
        about_dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about_dialog.present()

    def on_quit(self, action, param):
        self.quit()


class EmuWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super(EmuWindow, self).__init__(*args, **kwargs)

        hbox = Gtk.Box(spacing=6, visible=True)
        self.add(hbox)

        grid = Gtk.Grid(visible=True)
        hbox.pack_start(grid, True, True, 0)

        self.labels = []
        for y in range(8):
            row = []
            for x in range(8):
                label = Gtk.Label("", visible=True, hexpand=True)
                label.set_size_request(8, 8)
                row.append(label)
                grid.attach(label, x, y, 1, 1)
            self.labels.append(row)

        self.image1 = Gtk.Image(visible=True)
        hbox.pack_start(self.image1, True, True, 0)
        self.button1 = Gtk.Button(label="_Close", use_underline=True, visible=True)
        self.button1.connect('clicked', self.close_clicked)
        hbox.pack_start(self.button1, True, True, 0)

        self._screen = ScreenClient()
        self._pixbuf = None
        self._screen_thread = Thread(target=self._update_screen)
        self._screen_thread.daemon = True
        self._screen_thread.start()

    def close_clicked(self, button):
        self.quit()

    def _update_screen(self):
        while True:
            b = GLib.Bytes.new(np.ravel(self._screen.rgb_array))
            self._pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(b,
                colorspace=GdkPixbuf.Colorspace.RGB, has_alpha=False,
                bits_per_sample=8, width=8, height=8, rowstride=8 * 3)
            GLib.idle_add(self._copy_to_image)
            sleep(0.1)

    def _copy_to_image(self):
        if self._pixbuf:
            p = self._pixbuf.scale_simple(128, 128, GdkPixbuf.InterpType.NEAREST)
            self.image1.set_from_pixbuf(p)
            self.labels[0][0].override_background_color(
                Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 0, 0, 1))
        return False


def main():
    atexit.register(pkg_resources.cleanup_resources)
    GObject.threads_init()
    app = EmuApplication()
    app.run(sys.argv)

