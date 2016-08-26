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
str = type('')

import sys
import os
import io
import errno
from time import time, sleep


if sys.platform.startswith('win'):
    import ctypes
    kernel32 = ctypes.windll.kernel32
    DWORD = ctypes.c_ulong
    PROCESS_QUERY_INFORMATION = 0x0400
    ERROR_ACCESS_DENIED = 0x5
    ERROR_INVALID_PARAMETER = 0x57
    STILL_ACTIVE = 259

    def pid_exists(pid):
        h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, 0, pid)
        try:
            if not h:
                if kernel32.GetLastError() == ERROR_ACCESS_DENIED:
                    # If access is denied, there's obviously a process denying
                    # access...
                    return True
                elif kernel32.GetLastError() == ERROR_INVALID_PARAMETER:
                    # Invalid parameter is no such process
                    return False
                raise OSError('unable to get handle for pid %d' % pid)
            out = DWORD()
            if kernel32.GetExitCodeProcess(h, ctypes.byref(out)):
                return out.value == STILL_ACTIVE
            raise OSError('unable to query exit code for pid %d' % pid)
        finally:
            kernel32.CloseHandle(h)
else:
    def pid_exists(pid):
        if pid == 0:
            return True
        try:
            os.kill(pid, 0)
        except OSError as e:
            if e.errno == errno.ESRCH:
                return False
            elif e.errno == errno.EPERM:
                return True
            else:
                raise
        else:
            return True


def lock_filename():
    """
    Return the filename used as a lock-file by applications that can drive the
    emulation (currently sense_emu_gui and sense_play). On UNIX we try
    ``/dev/shm`` then fall back to ``/tmp``; on Windows we use whatever
    ``%TEMP%`` contains
    """
    fname = 'rpi-sense-emu-pid'
    if sys.platform.startswith('win'):
        # just use a temporary file on Windows
        return os.path.join(os.environ['TEMP'], fname)
    else:
        if os.path.exists('/dev/shm'):
            return os.path.join('/dev/shm', fname)
        else:
            return os.path.join('/tmp', fname)


class EmulatorLock(object):
    def __init__(self, name):
        self._filename = lock_filename()
        self.name = name # XXX not currently used

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.release()

    def acquire(self, timeout=None):
        """
        Acquire the emulator lock. This is expected to be called by anything
        wishing to drive the emulator's registers (sense_emu_gui and sense_play
        currently).
        """
        if self._is_stale():
            self._break_lock()
        self._write_pid()

    def release(self):
        """
        Release the emulator lock (presumably after :meth:`acquire`).
        """
        self._break_lock()

    def wait(self, timeout=None):
        """
        Wait for a process to acquire the lock. This is expected to be called
        by anything wishing to read the registers and wanting to ensure there's
        something driving them (i.e. any consumer of SenseHat).

        Returns ``True`` if the lock was acquired before *timeout* seconds
        elapsed, or ``False`` otherwise. If *timeout* is ``None`` (the default)
        wait indefinitely.
        """
        end = time()
        if timeout is None:
            wait = 0.1
        else:
            end += timeout
            wait = max(0, timeout / 10)
        while not self._is_held() or self._is_stale():
            if time() > end:
                return False
            sleep(wait)
        return True

    @property
    def mine(self):
        """
        Returns True if the current process holds the lock.
        """
        return self._read_pid() == os.getpid()

    def _is_held(self):
        return os.path.exists(self._filename)

    def _is_stale(self):
        # True if the lock file exists, but the PID it references doesn't
        pid = self._read_pid()
        if pid is not None:
            return not pid_exists(pid)
        else:
            return False

    def _break_lock(self):
        # Unconditionally delete the file
        try:
            os.unlink(self._filename)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    def _read_pid(self):
        try:
            lockfile = io.open(self._filename, 'rb')
        except IOError:
            return None
        else:
            try:
                return int(lockfile.readline().decode('ascii').strip())
            except ValueError:
                return None
            finally:
                lockfile.close()

    def _write_pid(self):
        try:
            lockfile = io.open(self._filename, 'x')
        except ValueError as e:
            # We're on py2.x or 3.2
            mode = 0o666
            lockfile = os.fdopen(os.open(
                self._filename, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode), 'w')
        lockfile.write('%d\n' % os.getpid())
        lockfile.close()

