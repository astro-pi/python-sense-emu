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
import atexit
import struct
import math
from time import time
from threading import Thread, Lock, Event

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib, GObject
import numpy as np
import pkg_resources

from .vector import Vector
from .screen import ScreenClient
from .imu import IMUServer
from .pressure import PressureServer
from .humidity import HumidityServer
from .stick import StickServer, SenseStick


def load_png(filename):
    loader = GdkPixbuf.PixbufLoader.new_with_type('png')
    loader.write(pkg_resources.resource_string(__name__, filename))
    loader.close()
    return loader.get_pixbuf()


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

        builder = Gtk.Builder.new_from_string(
            pkg_resources.resource_string(__name__, 'app_menu.xml').decode('utf-8'), -1)
        self.set_app_menu(builder.get_object('app-menu'))

        # Construct the emulator servers
        self.imu = IMUServer()
        self.pressure = PressureServer()
        self.humidity = HumidityServer()
        self.screen = ScreenClient()
        self.stick = StickServer()

    def do_shutdown(self):
        if self.window:
            self.window.close()
            self.window = None
        self.stick.close()
        self.screen.close()
        self.humidity.close()
        self.pressure.close()
        self.imu.close()
        Gtk.Application.do_shutdown(self)

    def do_activate(self):
        if not self.window:
            self.window = EmuWindow(application=self)
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


class EmuWindow(object):
    def __init__(self, application):
        super(EmuWindow, self).__init__()

        # Load the GUI definitions and connect the handlers
        builder = Gtk.Builder.new_from_string(
            pkg_resources.resource_string(__name__, 'sense_emu_gui.glade').decode('utf-8'), -1)
        builder.connect_signals(self)
        for name in (
            'window',
            'humidity',
            'pressure',
            'temperature',
            'left_button',
            'right_button',
            'up_button',
            'down_button',
            'enter_button',
            'screen_image',
            'yaw',
            'pitch',
            'roll',
            'yaw_image',
            'pitch_image',
            'roll_image',
            ):
            setattr(self, name, builder.get_object(name))
        self.application = application
        self.pitch.props.value = self.application.imu.orientation.x
        self.roll.props.value = self.application.imu.orientation.y
        self.yaw.props.value = self.application.imu.orientation.z
        self.humidity.props.value = self.application.humidity.humidity
        self.pressure.props.value = self.application.pressure.pressure
        self.temperature.props.value = self.application.humidity.temperature

        # Load graphics assets
        self.sense_image = load_png('sense_emu.png')
        self.pixel_grid = load_png('pixel_grid.png')
        self.yaw_image.set_from_pixbuf(load_png('yaw.png'))
        self.pitch_image.set_from_pixbuf(load_png('pitch.png'))
        self.roll_image.set_from_pixbuf(load_png('roll.png'))

        # Set up attributes for the joystick buttons
        self._stick_held_id = 0
        self.left_button.direction = SenseStick.KEY_LEFT
        self.right_button.direction = SenseStick.KEY_RIGHT
        self.up_button.direction = SenseStick.KEY_UP
        self.down_button.direction = SenseStick.KEY_DOWN
        self.enter_button.direction = SenseStick.KEY_ENTER

        # Set up a thread to constantly refresh the pixels from the screen
        # client object
        self._screen_pending = False
        self._screen_timestamp = 0.0
        self._screen_event = Event()
        self._screen_thread = Thread(target=self._update_screen)
        self._screen_thread.daemon = True
        self._screen_thread.start()

        self.window.show_all()

    @property
    def application(self):
        return self.window.props.application

    @application.setter
    def application(self, value):
        self.window.props.application = value

    def present(self):
        self.window.present()

    def close(self):
        try:
            self._screen_event.set()
            self._screen_thread.join()
        except AttributeError:
            # do_destroy gets called multiple times, and subsequent times lacks
            # the Python-added instance attributes
            pass
        self.window.destroy()

    def pressure_changed(self, adjustment):
        self.application.pressure.pressure = adjustment.props.value

    def humidity_changed(self, adjustment):
        self.application.humidity.humidity = adjustment.props.value

    def temperature_changed(self, adjustment):
        self.application.pressure.temperature = adjustment.props.value
        self.application.humidity.temperature = adjustment.props.value

    def orientation_changed(self, adjustment):
        self.application.imu.set_orientation(Vector(
            self.pitch.props.value,
            self.roll.props.value,
            self.yaw.props.value,
            ))

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
        self.application.stick.send(event_rec)

    def _update_screen(self):
        while True:
            if not self._screen_pending:
                ts = self.application.screen.timestamp
                if ts > self._screen_timestamp:
                    img = self.sense_image.copy()
                    pixels = GdkPixbuf.Pixbuf.new_from_bytes(
                        GLib.Bytes.new(self.application.screen.rgb_array.tostring()),
                        colorspace=GdkPixbuf.Colorspace.RGB, has_alpha=False,
                        bits_per_sample=8, width=8, height=8, rowstride=8 * 3)
                    pixels.composite(img, 31, 38, 128, 128, 31, 38, 16, 16,
                        GdkPixbuf.InterpType.NEAREST, 255)
                    self.pixel_grid.composite(img, 31, 38, 128, 128, 31, 38, 1, 1,
                        GdkPixbuf.InterpType.NEAREST, 255)
                    self._screen_pending = True
                    self._screen_timestamp = ts
                    GLib.idle_add(self._copy_to_image, img)
            if self._screen_event.wait(0.04):
                break

    def _copy_to_image(self, pixbuf):
        self.screen_image.set_from_pixbuf(pixbuf)
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

