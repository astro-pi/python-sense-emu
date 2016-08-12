# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Raspberry Pi Sense HAT Emulator library for the Raspberry Pi
# Copyright (c) 2016 Raspberry Pi Foundation <info@raspberrypi.org>
#
# This package is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This package is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )
native_str = str
str = type('')

import io
import os
import sys
import glob
import errno
import struct
import select
import inspect
import socket
from functools import wraps
from collections import namedtuple
from threading import Thread, Event
try:
    from queue import Queue, Empty
except:
    from Queue import Queue, Empty # py2.x
from time import sleep


DIRECTION_UP     = 'up'
DIRECTION_DOWN   = 'down'
DIRECTION_LEFT   = 'left'
DIRECTION_RIGHT  = 'right'
DIRECTION_MIDDLE = 'middle'

ACTION_PRESSED  = 'pressed'
ACTION_RELEASED = 'released'
ACTION_HELD     = 'held'


class InputEvent(namedtuple('InputEvent', ('timestamp', 'direction', 'action'))):
    """
    A :func:`~collections.namedtuple` derivative representing a joystick
    event. The following attributes are present:

    .. attribute:: timestamp

        The time at which the event occurred, represented as the number of
        seconds since the UNIX epoch (same output as :func:`~time.time`).

    .. attribute:: direction

        The direction in which the joystick was pushed (or released from), as
        one of the constants :data:`DIRECTION_UP`, :data:`DIRECTION_DOWN`,
        :data:`DIRECTION_LEFT`, :data:`DIRECTION_RIGHT`,
        :data:`DIRECTION_MIDDLE`

    .. attribute:: action

        The action that occurred, as one of the constants
        :data:`ACTION_PRESSED`, :data:`ACTION_RELEASED`, or
        :data:`ACTION_HELD`.
    """


def stick_address():
    """
    Return the socket address used represent the state of the emulated sense
    HAT's joystick. On UNIX we try ``/dev/shm`` then fall back to ``/tmp``
    (UNIX sockets); on Windows we use localhost.
    """
    fname = 'rpi-sense-emu-stick'
    if sys.platform.startswith('win'):
        # use UDP sockets on Windows
        return (socket.AF_INET, socket.SOCK_DGRAM, ('127.0.0.1', 53753))
    else:
        # use UNIX sockets everywhere else
        if os.path.exists('/dev/shm'):
            return (socket.AF_UNIX, socket.SOCK_DGRAM, os.path.join('/dev/shm', fname))
        else:
            return (socket.AF_UNIX, socket.SOCK_DGRAM, os.path.join('/tmp', fname))


def init_stick_client():
    """
    Opens a socket representing the state of the joystick as a series of evdev
    events. A file-like object is returned (readable like the character device
    representing the real joystick).

    A background thread is spawned to take care of connecting to the stick
    server (and to automatically handle re-connections in the case of
    termination). The thread is marked as a daemon thread so it won't prevent
    script shutdown.
    """
    family, sock_type, addr = stick_address()
    client = socket.socket(family, sock_type)
    if family == socket.AF_INET:
        client.bind(('127.0.0.1', 0))
    elif family == socket.AF_UNIX:
        fname = 'rpi-sense-emu-client-%d' % os.getpid()
        addr_path = os.path.dirname(addr)
        try:
            os.unlink(os.path.join(addr_path, fname))
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
        client.bind(os.path.join(addr_path, fname))
    if not client.getsockname():
        raise RuntimeError('Failed to create client socket for stick emulation')
    # Start up a background thread which persistently attempts to connect to
    # the server and pings it with "hello" to notify it that we want stick
    # events. This must be persistent in case the emulating client is stopped
    # and restarted
    def ping_server():
        while True:
            try:
                client.connect(addr)
                client.send(b'hello')
            except socket.error as e:
                if e.errno not in (errno.ENOENT, errno.ENOTCONN, errno.ECONNREFUSED):
                    raise
            sleep(1)
    thread = Thread(target=ping_server)
    thread.daemon = True
    thread.start()
    # Construct file object on top of the socket which we'll return as the
    # result
    return client.makefile('rb', 0)


class SenseStick(object):
    """
    Represents the joystick on the Sense HAT.
    """
    SENSE_HAT_EVDEV_NAME = 'Raspberry Pi Sense HAT Joystick'
    EVENT_FORMAT = native_str('llHHI')
    EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

    EV_KEY = 0x01

    STATE_RELEASE = 0
    STATE_PRESS = 1
    STATE_HOLD = 2

    KEY_UP = 103
    KEY_LEFT = 105
    KEY_RIGHT = 106
    KEY_DOWN = 108
    KEY_ENTER = 28

    def __init__(self):
        self._stick_file = self._stick_device()
        self._callbacks = {}
        self._callback_thread = None
        self._callback_event = Event()

    def close(self):
        if self._stick_file:
            self._callbacks.clear()
            self._start_stop_thread()
            self._stick_file.close()
            self._stick_file = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def _stick_device(self):
        """
        Discovers the filename of the evdev device that represents the Sense
        HAT's joystick.
        """
        return init_stick_client()

    def _read(self):
        """
        Reads a single event from the joystick, blocking until one is
        available. Returns ``None`` if a non-key event was read, or an
        :class:`InputEvent` tuple describing the event otherwise.
        """
        event = self._stick_file.read(self.EVENT_SIZE)
        (tv_sec, tv_usec, type, code, value) = struct.unpack(self.EVENT_FORMAT, event)
        if type == self.EV_KEY:
            return InputEvent(
                timestamp=tv_sec + (tv_usec / 1000000),
                direction={
                    self.KEY_UP:    DIRECTION_UP,
                    self.KEY_DOWN:  DIRECTION_DOWN,
                    self.KEY_LEFT:  DIRECTION_LEFT,
                    self.KEY_RIGHT: DIRECTION_RIGHT,
                    self.KEY_ENTER: DIRECTION_MIDDLE,
                    }[code],
                action={
                    self.STATE_PRESS:   ACTION_PRESSED,
                    self.STATE_RELEASE: ACTION_RELEASED,
                    self.STATE_HOLD:    ACTION_HELD,
                    }[value])
        else:
            return None

    def _wait(self, timeout=None):
        """
        Waits *timeout* seconds until an event is available from the
        joystick. Returns ``True`` if an event became available, and ``False``
        if the timeout expired.
        """
        r, w, x = select.select([self._stick_file], [], [], timeout)
        return bool(r)

    def _wrap_callback(self, fn):
        # Shamelessley nicked (with some variation) from GPIO Zero :)
        @wraps(fn)
        def wrapper(event):
            return fn()

        if fn is None:
            return None
        elif not callable(fn):
            raise ValueError('value must be None or a callable')
        elif inspect.isbuiltin(fn):
            # We can't introspect the prototype of builtins. In this case we
            # assume that the builtin has no (mandatory) parameters; this is
            # the most reasonable assumption on the basis that pre-existing
            # builtins have no knowledge of InputEvent, and the sole parameter
            # we would pass is an InputEvent
            return wrapper
        else:
            # Try binding ourselves to the argspec of the provided callable.
            # If this works, assume the function is capable of accepting no
            # parameters and that we have to wrap it to ignore the event
            # parameter
            try:
                inspect.getcallargs(fn)
                return wrapper
            except TypeError:
                try:
                    # If the above fails, try binding with a single tuple
                    # parameter. If this works, return the callback as is
                    inspect.getcallargs(fn, ())
                    return fn
                except TypeError:
                    raise ValueError(
                        'value must be a callable which accepts up to one '
                        'mandatory parameter')

    def _start_stop_thread(self):
        if self._callbacks and not self._callback_thread:
            self._callback_event.clear()
            self._callback_thread = Thread(target=self._callback_run)
            self._callback_thread.daemon = True
            self._callback_thread.start()
        elif not self._callbacks and self._callback_thread:
            self._callback_event.set()
            self._callback_thread.join()
            self._callback_thread = None

    def _callback_run(self):
        while not self._callback_event.wait(0):
            event = self._read()
            if event:
                callback = self._callbacks.get(event.direction)
                if callback:
                    callback(event)
                callback = self._callbacks.get('*')
                if callback:
                    callback(event)

    def wait_for_event(self, emptybuffer=False):
        """
        Waits until a joystick event becomes available.  Returns the event, as
        an :class:`InputEvent` tuple.

        If *emptybuffer* is ``True`` (it defaults to ``False``), any pending
        events will be thrown away first. This is most useful if you are only
        interested in "pressed" events.
        """
        if emptybuffer:
            while self._wait(0):
                self._read()
        while self._wait():
            event = self._read()
            if event:
                return event

    def get_events(self):
        """
        Returns a list of all joystick events that have occurred since the last
        call to :meth:`get_events`. The list contains events in the order that
        they occurred. If no events have occurred in the intervening time, the
        result is an empty list.
        """
        result = []
        while self._wait(0):
            event = self._read()
            if event:
                result.append(event)
        return result

    @property
    def direction_up(self):
        """
        The function to be called when the joystick is pushed up. The function
        can either take a parameter which will be the :class:`InputEvent` tuple
        that has occurred, or the function can take no parameters at all.

        Assign ``None`` to prevent this event from being fired.
        """
        return self._callbacks.get(DIRECTION_UP)

    @direction_up.setter
    def direction_up(self, value):
        self._callbacks[DIRECTION_UP] = self._wrap_callback(value)
        self._start_stop_thread()

    @property
    def direction_down(self):
        """
        The function to be called when the joystick is pushed down. The
        function can either take a parameter which will be the
        :class:`InputEvent` tuple that has occurred, or the function can take
        no parameters at all.

        Assign ``None`` to prevent this event from being fired.
        """
        return self._callbacks.get(DIRECTION_DOWN)

    @direction_down.setter
    def direction_down(self, value):
        self._callbacks[DIRECTION_DOWN] = self._wrap_callback(value)
        self._start_stop_thread()

    @property
    def direction_left(self):
        """
        The function to be called when the joystick is pushed left. The
        function can either take a parameter which will be the
        :class:`InputEvent` tuple that has occurred, or the function can take
        no parameters at all.

        Assign ``None`` to prevent this event from being fired.
        """
        return self._callbacks.get(DIRECTION_LEFT)

    @direction_left.setter
    def direction_left(self, value):
        self._callbacks[DIRECTION_LEFT] = self._wrap_callback(value)
        self._start_stop_thread()

    @property
    def direction_right(self):
        """
        The function to be called when the joystick is pushed right. The
        function can either take a parameter which will be the
        :class:`InputEvent` tuple that has occurred, or the function can take
        no parameters at all.

        Assign ``None`` to prevent this event from being fired.
        """
        return self._callbacks.get(DIRECTION_RIGHT)

    @direction_right.setter
    def direction_right(self, value):
        self._callbacks[DIRECTION_RIGHT] = self._wrap_callback(value)
        self._start_stop_thread()

    @property
    def direction_middle(self):
        """
        The function to be called when the joystick middle click is pressed.
        The function can either take a parameter which will be the
        :class:`InputEvent` tuple that has occurred, or the function can take
        no parameters at all.

        Assign ``None`` to prevent this event from being fired.
        """
        return self._callbacks.get(DIRECTION_MIDDLE)

    @direction_middle.setter
    def direction_middle(self, value):
        self._callbacks[DIRECTION_MIDDLE] = self._wrap_callback(value)
        self._start_stop_thread()

    @property
    def direction_any(self):
        """
        The function to be called when the joystick is used. The function can
        either take a parameter which will be the :class:`InputEvent` tuple
        that has occurred, or the function can take no parameters at all.

        This event will always be called *after* events associated with a
        specific action. Assign ``None`` to prevent this event from being
        fired.
        """
        return self._callbacks.get('*')

    @direction_any.setter
    def direction_any(self, value):
        self._callbacks['*'] = self._wrap_callback(value)
        self._start_stop_thread()


class StickServer(object):
    def __init__(self):
        family, sock_type, addr = stick_address()
        server = socket.socket(family, sock_type)
        if family == socket.AF_UNIX:
            try:
                # Kill any pre-existing socket
                os.unlink(addr)
            except OSError:
                pass
        server.bind(addr)
        self._stop = Event()
        self._queue = Queue()
        self._thread = Thread(target=self._serve, args=(server,))
        self._thread.daemon = True
        self._thread.start()

    def _serve(self, server):
        try:
            clients = set()
            while not self._stop.wait(0):
                # Pick up any new clients waiting to receive events
                while select.select([server], [], [], 0)[0]:
                    data, addr = server.recvfrom(64)
                    if data == b'hello':
                        clients.add(addr)
                try:
                    # Grab any data waiting to be sent to clients; we put the
                    # only pause for the thread here to ensure timely response
                    # to events being placed in the queue
                    buf = self._queue.get(timeout=0.1)
                except Empty:
                    pass
                else:
                    # Send the event to all connected clients (pruning any that
                    # fail)
                    for client in list(clients):
                        try:
                            server.sendto(buf, client)
                        except socket.error as e:
                            if e.errno in (errno.ENOENT, errno.ECONNREFUSED):
                                clients.remove(client)
        finally:
            family = server.family
            addr = server.getsockname()
            server.close()
            if family == socket.AF_UNIX:
                # Only works because socket name is guaranteed to be absolute
                os.unlink(addr)

    def close(self):
        if self._thread:
            self._stop.set()
            self._thread.join()

    def send(self, buf):
        self._queue.put(buf)

