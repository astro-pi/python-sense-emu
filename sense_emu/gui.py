from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )
str = type('')


import sys
import atexit

import pkg_resources
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, Gio, GLib


class EmuApplication(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super(EmuApplication, self).__init__(
                *args, application_id='org.raspberrypi.sense_hat_emu',
                flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                **kwargs)
        self.window = None

    def do_startup(self):
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

        max_action = Gio.SimpleAction.new_stateful('maximize', None,
                GLib.Variant.new_boolean(False))
        max_action.connect('change-state', self.on_maximize_toggle)
        self.add_action(max_action)

        self.connect('notify::is-maximized',
            lambda obj, pspec: max_action.set_state(
                GLib.Variant.new_boolean(obj.props.is_maximized))
            )

        lbl_variant = GLib.Variant.new_string('String 1')
        lbl_action = Gio.SimpleAction.new_stateful('change_label', lbl_variant.get_type(), lbl_variant)
        lbl_action.connect('change-state', self.on_change_label_state)
        self.add_action(lbl_action)

        self.label = Gtk.Label(label=lbl_variant.get_string(), margin=30)
        self.add(self.label)
        self.label.show()

    def on_change_label_state(self, action, value):
        action.set_state(value)
        self.label.set_text(value.get_string())

    def on_maximize_toggle(self, action, value):
        action.set_state(value)
        if value.get_boolean():
            self.maximize()
        else:
            self.unmaximize()


def main():
    atexit.register(pkg_resources.cleanup_resources)
    app = EmuApplication()
    app.run(sys.argv)

