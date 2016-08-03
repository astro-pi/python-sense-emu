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


import io
import os
import sys
import atexit
import struct
import math
from time import time, sleep
from threading import Thread, Lock, Event

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib, GObject
import numpy as np
import pkg_resources

from . import __version__, __author__, __author_email__, __url__
from .screen import ScreenClient
from .imu import IMUServer
from .pressure import PressureServer
from .humidity import HumidityServer
from .stick import StickServer, SenseStick
from .common import HEADER_REC, DATA_REC, DataRecord


def load_image(filename, format='png'):
    loader = GdkPixbuf.PixbufLoader.new_with_type(format)
    loader.write(pkg_resources.resource_string(__name__, filename))
    loader.close()
    return loader.get_pixbuf()


class EmuApplication(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super(EmuApplication, self).__init__(
                *args, application_id='org.raspberrypi.sense_hat_emu',
                flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                **kwargs)
        GLib.set_application_name('Sense HAT Emulator')
        self.window = None

    def do_startup(self):
        # super-call needs to be in this form?!
        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new('about', None)
        action.connect('activate', self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new('play', None)
        action.connect('activate', self.on_play)
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
            self.window.destroy()
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
        logo = load_image('sense_emu_gui.svg', format='svg')
        about_dialog = Gtk.AboutDialog(
            transient_for=self.window, modal=True,
            authors=['%s <%s>' % (__author__, __author_email__)],
            license_type=Gtk.License.BSD, logo=logo,
            version=__version__, website=__url__)
        about_dialog.run()
        about_dialog.destroy()

    def on_play(self, action, param):
        open_dialog = Gtk.FileChooserDialog(
            title='Select the recording to play', transient_for=self.window,
            action=Gtk.FileChooserAction.OPEN)
        open_dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        open_dialog.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
        try:
            response = open_dialog.run()
            open_dialog.hide()
            if response == Gtk.ResponseType.ACCEPT:
                self.window.play(open_dialog.get_filename())
        finally:
            open_dialog.destroy()

    def on_quit(self, action, param):
        self.quit()


class BuilderUi(object):
    def __init__(self, owner, filename):
        # Load the GUI definitions (see __getattr__ for how we tie the loaded
        # objects into instance variables) and connect all handlers to methods
        # on this object
        self._builder = Gtk.Builder.new_from_string(
            pkg_resources.resource_string(__name__, filename).decode('utf-8'), -1)
        self._builder.connect_signals(owner)

    def __getattr__(self, name):
        result = self._builder.get_object(name)
        if result is None:
            raise AttributeError('No such attribute %r' % name)
        setattr(self, name, result)
        return result


class EmuWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super(EmuWindow, self).__init__(*args, **kwargs)

        # Build the UI; this is a bit round-about because of Gtk's weird UI
        # handling. One can't just use a UI file to setup an existing Window
        # instance (as in Qt); instead one must use a separate handler object
        # (in which case overriding do_destroy is impossible) or construct a
        # whole new Window, remove its components, add them to ourselves and
        # then ditch the Window.
        self._ui = BuilderUi(self, 'sense_emu_gui.glade')
        self.ui.window.remove(self.ui.root_grid)
        self.add(self.ui.root_grid)
        self.ui.window.destroy()

        # Set up the objects for the playback thread
        self._play_event = Event()
        self._play_thread = None

        # Set initial positions on sliders (and add some marks)
        self.ui.pitch_scale.add_mark(0, Gtk.PositionType.BOTTOM, None)
        self.ui.roll_scale.add_mark(0, Gtk.PositionType.BOTTOM, None)
        self.ui.yaw_scale.add_mark(0, Gtk.PositionType.BOTTOM, None)
        self.ui.pitch.props.value = self.props.application.imu.orientation[0]
        self.ui.roll.props.value = self.props.application.imu.orientation[1]
        self.ui.yaw.props.value = self.props.application.imu.orientation[2]
        self.ui.humidity.props.value = self.props.application.humidity.humidity
        self.ui.pressure.props.value = self.props.application.pressure.pressure
        self.ui.temperature.props.value = self.props.application.humidity.temperature

        # Load graphics assets
        self.sense_image = load_image('sense_emu.png')
        self.pixel_grid = load_image('pixel_grid.png')
        self.ui.yaw_image.set_from_pixbuf(load_image('yaw.png'))
        self.ui.pitch_image.set_from_pixbuf(load_image('pitch.png'))
        self.ui.roll_image.set_from_pixbuf(load_image('roll.png'))

        # Set up attributes for the joystick buttons
        self._stick_held_id = 0
        self.ui.left_button.direction = SenseStick.KEY_LEFT
        self.ui.right_button.direction = SenseStick.KEY_RIGHT
        self.ui.up_button.direction = SenseStick.KEY_UP
        self.ui.down_button.direction = SenseStick.KEY_DOWN
        self.ui.enter_button.direction = SenseStick.KEY_ENTER

        # Set up a thread to constantly refresh the pixels from the screen
        # client object
        self._screen_pending = False
        self._screen_timestamp = 0.0
        self._screen_event = Event()
        self._screen_thread = Thread(target=self._screen_run)
        self._screen_thread.daemon = True
        self._screen_thread.start()

    @property
    def ui(self):
        return self._ui

    def do_destroy(self):
        try:
            self._play_stop()
            self._screen_event.set()
            self._screen_thread.join()
        except AttributeError:
            # do_destroy gets called multiple times, and subsequent times lacks
            # the Python-added instance attributes
            pass
        Gtk.ApplicationWindow.do_destroy(self)

    def pressure_changed(self, adjustment):
        if not self._play_thread:
            self.props.application.pressure.set_values(
                self.ui.pressure.props.value,
                self.ui.temperature.props.value,
                )

    def humidity_changed(self, adjustment):
        if not self._play_thread:
            self.props.application.humidity.set_values(
                self.ui.humidity.props.value,
                self.ui.temperature.props.value,
                )

    def temperature_changed(self, adjustment):
        if not self._play_thread:
            self.pressure_changed(adjustment)
            self.humidity_changed(adjustment)

    def orientation_changed(self, adjustment):
        if not self._play_thread:
            self.props.application.imu.set_orientation((
                self.ui.pitch.props.value,
                self.ui.roll.props.value,
                self.ui.yaw.props.value,
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
        self.props.application.stick.send(event_rec)

    def _screen_run(self):
        # This method runs in the background _screen_thread
        while True:
            # Only update the screen if there's no idle callback pending from
            # a prior update
            if not self._screen_pending:
                # Only update if the screen's modification timestamp indicates
                # that the data has changed since last time
                ts = self.props.application.screen.timestamp
                if ts > self._screen_timestamp:
                    img = self.sense_image.copy()
                    pixels = GdkPixbuf.Pixbuf.new_from_bytes(
                        GLib.Bytes.new(self.props.application.screen.rgb_array.tostring()),
                        colorspace=GdkPixbuf.Colorspace.RGB, has_alpha=False,
                        bits_per_sample=8, width=8, height=8, rowstride=8 * 3)
                    pixels.composite(img, 31, 38, 128, 128, 31, 38, 16, 16,
                        GdkPixbuf.InterpType.NEAREST, 255)
                    self.pixel_grid.composite(img, 31, 38, 128, 128, 31, 38, 1, 1,
                        GdkPixbuf.InterpType.NEAREST, 255)
                    self._screen_pending = True
                    self._screen_timestamp = ts
                    # GTK updates must be done by the main thread; schedule
                    # the image to be redrawn when the app is idle. It would
                    # be better to use custom signals for this ... but then
                    # pixman bugs start appearing
                    self._screen_pixbuf = img
                    GLib.idle_add(self._update_screen, img)
            # The following wait ensures a maximum update rate of 25fps (the
            # actual HAT is faster, but on small Pi's increasing the rate
            # reduces performance)
            if self._screen_event.wait(0.04):
                break

    def _update_screen(self, pixbuf):
        self.ui.screen_image.set_from_pixbuf(self._screen_pixbuf)
        self._screen_pending = False
        return False

    def _play_run(self, f):
        try:
            rec_total = (f.seek(0, io.SEEK_END) - HEADER_REC.size) // DATA_REC.size
            f.seek(0)
            skipped = 0
            for rec, data in enumerate(self._play_source(f)):
                now = time()
                if data.timestamp < now:
                    skipped += 1
                    continue
                else:
                    if self._play_event.wait(data.timestamp - now):
                        break
                self.props.application.pressure.set_values(data.pressure, data.ptemp)
                self.props.application.humidity.set_values(data.humidity, data.htemp)
                self.props.application.imu.set_imu_values(
                    (data.ax, data.ay, data.az),
                    (data.gx, data.gy, data.gz),
                    (data.cx, data.cy, data.cz),
                    (data.ox, data.oy, data.oz),
                    )
                # Again, would be better to use custom signals here but
                # attempting to do so just results in seemingly random
                # segfaults ...
                GLib.idle_add(self._play_update_controls, rec / rec_total)
        finally:
            f.close()
            # Get the main thread to re-enable the controls at the end of
            # playback
            GLib.idle_add(self._play_controls_finish)

    def play_stop_clicked(self, button):
        self._play_stop()

    def _play_stop(self):
        if self._play_thread:
            self._play_event.set()
            self._play_thread.join()
            self._play_thread = None

    def _play_source(self, f):
        magic, ver, offset = HEADER_REC.unpack(f.read(HEADER_REC.size))
        if magic != b'SENSEHAT':
            raise IOError('Invalid magic number at start of input')
        if ver != 1:
            raise IOError('Unrecognized file version number (%d)' % ver)
        offset = time() - offset
        while True:
            buf = f.read(DATA_REC.size)
            if not buf:
                break
            elif len(buf) < DATA_REC.size:
                raise IOError('Incomplete data record at end of file')
            else:
                data = DataRecord(*DATA_REC.unpack(buf))
                yield data._replace(timestamp=data.timestamp + offset)

    def _play_controls_setup(self, filename):
        # Disable all the associated user controls while playing back
        self.ui.environ_box.props.sensitive = False
        self.ui.gyro_grid.props.sensitive = False
        # Disable simulation threads as we're going to manipulate the
        # values precisely
        self.props.application.pressure.simulate_noise = False
        self.props.application.humidity.simulate_noise = False
        self.props.application.imu.simulate_world = False
        # Show the playback bar
        self.ui.play_label.props.label = "Playing %s" % os.path.basename(filename)
        self.ui.play_progressbar.props.fraction = 0.0
        self.ui.play_box.props.visible = True

    def _play_controls_finish(self):
        self.ui.play_box.props.visible = False
        self.props.application.imu.simulate_world = True
        self.props.application.humidity.simulate_noise = True
        self.props.application.pressure.simulate_noise = True
        self.ui.environ_box.props.sensitive = True
        self.ui.gyro_grid.props.sensitive = True
        self._play_stop()

    def _play_update_controls(self, fraction):
        self.ui.play_progressbar.props.fraction = fraction
        if not math.isnan(self.props.application.humidity.temperature):
            self.ui.temperature.props.value = self.props.application.humidity.temperature
        if not math.isnan(self.props.application.pressure.pressure):
            self.ui.pressure.props.value = self.props.application.pressure.pressure
        if not math.isnan(self.props.application.humidity.humidity):
            self.ui.humidity.props.value = self.props.application.humidity.humidity
        self.ui.yaw.props.value = math.degrees(self.props.application.imu.orientation[2])
        self.ui.pitch.props.value = math.degrees(self.props.application.imu.orientation[1])
        self.ui.roll.props.value = math.degrees(self.props.application.imu.orientation[0])
        return False

    def play(self, filename):
        self._play_stop()
        self._play_controls_setup(filename)
        self._play_thread = Thread(target=self._play_run, args=(io.open(filename, 'rb'),))
        self._play_event.clear()
        self._play_thread.start()


def main():
    # ensure any resources we extract get cleaned up interpreter shutdown
    atexit.register(pkg_resources.cleanup_resources)
    # threads_init isn't required since PyGObject 3.10.2, but just in case
    # we're on something ancient...
    GObject.threads_init()
    app = EmuApplication()
    app.run(sys.argv)

