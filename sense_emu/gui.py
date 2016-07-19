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
import struct
import math
from time import time
from threading import Thread, Lock, Event

import numpy as np
import pkg_resources
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib, GObject

from .screen import ScreenClient
from .imu import PressureServer, HumidityServer
from .stick import StickServer, SenseStick


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

        # Construct the emulator servers
        self.pressure = PressureServer()
        self.humidity = HumidityServer()
        self.screen = ScreenClient()
        self.stick = StickServer()

    def do_shutdown(self):
        if self.window:
            self.window.destroy()
            self.window = None
        self.stick.close()
        self.screen.close()
        self.humidity.close()
        self.pressure.close()
        Gtk.Application.do_shutdown(self)

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

        hbox = Gtk.Box(spacing=6, visible=True)
        self.add(hbox)

        # Add the pixel-image
        self.screen_image = Gtk.Image(visible=True)
        hbox.pack_start(self.screen_image, True, True, 0)

        # Add the temperature slider
        vbox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL, visible=True)
        vbox.pack_start(Gtk.Label(label="Temp (°C)", visible=True), False, False, 0)
        adj = Gtk.Adjustment(
            lower=-30, upper=105, value=self.app.humidity.temperature,
            step_increment=1, page_increment=10)
        adj.connect('value_changed' ,self.temperature_changed)
        temperature_scale = Gtk.Scale(
            orientation=Gtk.Orientation.VERTICAL, adjustment=adj,
            inverted=True, visible=True)
        vbox.pack_start(temperature_scale, True, True, 0)
        hbox.pack_start(vbox, True, True, 0)

        # Add the pressure slider
        vbox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL, visible=True)
        vbox.pack_start(Gtk.Label(label="Pressure (hPa)", visible=True), False, False, 0)
        adj = Gtk.Adjustment(
            lower=260, upper=1260, value=self.app.pressure.pressure,
            step_increment=1, page_increment=100)
        adj.connect('value_changed', self.pressure_changed)
        pressure_scale = Gtk.Scale(
            orientation=Gtk.Orientation.VERTICAL, adjustment=adj,
            inverted=True, visible=True)
        vbox.pack_start(pressure_scale, True, True, 0)
        hbox.pack_start(vbox, True, True, 0)

        # Add the humidity slider
        vbox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL, visible=True)
        vbox.pack_start(Gtk.Label(label="Humidity (%)", visible=True), False, False, 0)
        adj = Gtk.Adjustment(
            lower=0, upper=100, value=self.app.humidity.humidity,
            step_increment=1, page_increment=10)
        adj.connect('value_changed', self.humidity_changed)
        humidity_scale = Gtk.Scale(
            orientation=Gtk.Orientation.VERTICAL, adjustment=adj,
            inverted=True, visible=True)
        vbox.pack_start(humidity_scale, True, True, 0)
        hbox.pack_start(vbox, True, True, 0)

        # Add the joystick grid
        vbox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL, visible=True)
        vbox.pack_start(Gtk.Label(label="Joystick", visible=True), False, False, 0)
        left_button = Gtk.Button(label="←", visible=True)
        left_button.direction = SenseStick.KEY_LEFT
        right_button = Gtk.Button(label="→", visible=True)
        right_button.direction = SenseStick.KEY_RIGHT
        up_button = Gtk.Button(label="↑", visible=True)
        up_button.direction = SenseStick.KEY_UP
        down_button = Gtk.Button(label="↓", visible=True)
        down_button.direction = SenseStick.KEY_DOWN
        enter_button = Gtk.Button(label="↵", visible=True)
        enter_button.direction = SenseStick.KEY_ENTER
        for button in (
                left_button,
                right_button,
                up_button,
                down_button,
                enter_button):
            button.connect('button-press-event', self.stick_pressed)
            button.connect('button-release-event', self.stick_released)
        grid = Gtk.Grid(visible=True)
        grid.attach(up_button, 1, 0, 1, 1)
        grid.attach(left_button, 0, 1, 1, 1)
        grid.attach(enter_button, 1, 1, 1, 1)
        grid.attach(right_button, 2, 1, 1, 1)
        grid.attach(down_button, 1, 2, 1, 1)
        vbox.pack_start(grid, False, False, 0)
        hbox.pack_start(vbox, True, False, 0)

        quit_button = Gtk.Button(label="_Quit", use_underline=True, visible=True)
        quit_button.connect('clicked', self.close_clicked)
        hbox.pack_start(quit_button, True, True, 0)

        # Set up a thread to constantly refresh the pixels from the screen
        # client object
        self._screen_pb = None
        self._screen_pending = False
        self._screen_timestamp = 0.0
        self._screen_event = Event()
        self._screen_thread = Thread(target=self._update_screen)
        self._screen_thread.daemon = True
        self._screen_thread.start()

        # Instance variable to contain the ID of the repeater used for stick
        # held events
        self._stick_held_id = 0

    def do_destroy(self):
        try:
            self._screen_event.set()
            self._screen_thread.join()
        except AttributeError:
            # do_destroy gets called multiple times, and subsequent times lacks
            # the Python-added instance attributes
            pass
        Gtk.ApplicationWindow.do_destroy(self)

    def close_clicked(self, button):
        self.app.quit()

    def pressure_changed(self, adjustment):
        self.app.pressure.pressure = adjustment.props.value

    def humidity_changed(self, adjustment):
        self.app.humidity.humidity = adjustment.props.value

    def temperature_changed(self, adjustment):
        self.app.pressure.temperature = adjustment.props.value
        self.app.humidity.temperature = adjustment.props.value

    def stick_pressed(self, button, event):
        # XXX This shouldn't be necessary, but GTK seems to fire stick_pressed
        # twice in quick succession (with no intervening stick_released) when
        # a button is double-clicked
        if self._stick_held_id:
            GLib.source_remove(self._stick_held_id)
        self._stick_held_id = GLib.timeout_add(250, self.stick_held_first, button)
        self._stick_send(button.direction, SenseStick.STATE_PRESS)
        return False

    def stick_released(self, button, event):
        if self._stick_held_id:
            GLib.source_remove(self._stick_held_id)
            self._stick_held_id = 0
        self._stick_send(button.direction, SenseStick.STATE_RELEASE)
        return False

    def stick_held_first(self, button):
        self._stick_held_id = GLib.timeout_add(50, self.stick_held, button)
        self._stick_send(button.direction, SenseStick.STATE_HOLD)
        return False

    def stick_held(self, button):
        self._stick_send(button.direction, SenseStick.STATE_HOLD)
        return True

    def _stick_send(self, direction, action):
        tv_usec, tv_sec = math.modf(time())
        tv_usec *= 1000000
        event_rec = struct.pack(SenseStick.EVENT_FORMAT,
            int(tv_sec), int(tv_usec), SenseStick.EV_KEY, direction, action)
        self.app.stick.send(event_rec)

    def _update_screen(self):
        while True:
            if not self._screen_pending:
                ts = self.app.screen.timestamp
                if ts > self._screen_timestamp:
                    self._screen_pb = GdkPixbuf.Pixbuf.new_from_bytes(
                        GLib.Bytes.new(np.ravel(self.app.screen.rgb_array)),
                        colorspace=GdkPixbuf.Colorspace.RGB, has_alpha=False,
                        bits_per_sample=8, width=8, height=8, rowstride=8 * 3)
                    self._screen_pending = True
                    self._screen_timestamp = ts
                    GLib.idle_add(self._copy_to_image)
            if self._screen_event.wait(0.04):
                break

    def _copy_to_image(self):
        p = self._screen_pb.scale_simple(128, 128, GdkPixbuf.InterpType.NEAREST)
        self.screen_image.set_from_pixbuf(p)
        self._screen_pending = False
        return False


def main():
    # ensure any resources we extract get cleaned up interpreter shutdown
    atexit.register(pkg_resources.cleanup_resources)
    # threads_init isn't required since PyGObject 3.10.2, but just in case
    # we're on something ancient...
    GObject.threads_init()
    app = EmuApplication()
    app.run(sys.argv)

