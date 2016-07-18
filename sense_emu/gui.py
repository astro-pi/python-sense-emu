# vim: set et sw=4 sts=4 fileencoding=utf-8:

from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )
str = type('')


import sys
import atexit
from threading import Thread, Lock, Event

import numpy as np
import pkg_resources
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib, GObject

from .screen import ScreenClient
from .imu import PressureServer, HumidityServer


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

        self.app = kwargs['application']
        self._pressure = PressureServer()
        self._humidity = HumidityServer()
        self._screen = ScreenClient()

        hbox = Gtk.Box(spacing=6, visible=True)
        self.add(hbox)

        self.screen_image = Gtk.Image(visible=True)
        hbox.pack_start(self.screen_image, True, True, 0)

        vbox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL, visible=True)
        vbox.pack_start(Gtk.Label(label="Temp (°C)", visible=True), False, False, 0)
        adj = Gtk.Adjustment(
            lower=-30, upper=105, value=self._humidity.temperature,
            step_increment=1, page_increment=10)
        adj.connect('value_changed' ,self.temperature_changed)
        temperature_scale = Gtk.Scale(
            orientation=Gtk.Orientation.VERTICAL, adjustment=adj,
            inverted=True, visible=True)
        vbox.pack_start(temperature_scale, True, True, 0)
        hbox.pack_start(vbox, True, True, 0)

        vbox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL, visible=True)
        vbox.pack_start(Gtk.Label(label="Pressure (hPa)", visible=True), False, False, 0)
        adj = Gtk.Adjustment(
            lower=260, upper=1260, value=self._pressure.pressure,
            step_increment=1, page_increment=100)
        adj.connect('value_changed', self.pressure_changed)
        pressure_scale = Gtk.Scale(
            orientation=Gtk.Orientation.VERTICAL, adjustment=adj,
            inverted=True, visible=True)
        vbox.pack_start(pressure_scale, True, True, 0)
        hbox.pack_start(vbox, True, True, 0)

        vbox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL, visible=True)
        vbox.pack_start(Gtk.Label(label="Humidity (%)", visible=True), False, False, 0)
        adj = Gtk.Adjustment(
            lower=0, upper=100, value=self._humidity.humidity,
            step_increment=1, page_increment=10)
        adj.connect('value_changed', self.humidity_changed)
        humidity_scale = Gtk.Scale(
            orientation=Gtk.Orientation.VERTICAL, adjustment=adj,
            inverted=True, visible=True)
        vbox.pack_start(humidity_scale, True, True, 0)
        hbox.pack_start(vbox, True, True, 0)

        quit_button = Gtk.Button(label="_Quit", use_underline=True, visible=True)
        quit_button.connect('clicked', self.close_clicked)
        hbox.pack_start(quit_button, True, True, 0)

        self._screen_pb = None
        self._screen_event = Event()
        self._screen_thread = Thread(target=self._update_screen)
        self._screen_thread.daemon = True
        self._screen_thread.start()

        self.connect('delete-event', self.delete_window)

    def pressure_changed(self, adjustment):
        self._pressure.pressure = adjustment.props.value

    def humidity_changed(self, adjustment):
        self._humidity.humidity = adjustment.props.value

    def temperature_changed(self, adjustment):
        self._pressure.temperature = adjustment.props.value
        self._humidity.temperature = adjustment.props.value

    def delete_window(self, window):
        self._screen_event.set()
        self._screen_thread.join()
        self._humidity.close()
        self._pressure.close()

    def close_clicked(self, button):
        self.app.quit()

    def _update_screen(self):
        while True:
            self._screen_pb = GdkPixbuf.Pixbuf.new_from_bytes(
                GLib.Bytes.new(np.ravel(self._screen.rgb_array)),
                colorspace=GdkPixbuf.Colorspace.RGB, has_alpha=False,
                bits_per_sample=8, width=8, height=8, rowstride=8 * 3)
            GLib.idle_add(self._copy_to_image)
            if self._screen_event.wait(0.1):
                break

    def _copy_to_image(self):
        if self._screen_pb:
            p = self._screen_pb.scale_simple(128, 128, GdkPixbuf.InterpType.NEAREST)
            self.screen_image.set_from_pixbuf(p)
        return False


def main():
    atexit.register(pkg_resources.cleanup_resources)
    GObject.threads_init()
    app = EmuApplication()
    app.run(sys.argv)

