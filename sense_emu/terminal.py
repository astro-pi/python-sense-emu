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

"""
Defines base classes for command line utilities.

This module define a TerminalApplication class which provides common facilities
to command line applications: a help screen, universal file globbing, response
file handling, and common logging configuration and options.
"""

import sys
import io
import os
import argparse
import textwrap
import logging
import locale
import traceback
import configparser

from .i18n import init_i18n, _

try:
    # Optionally import argcomplete (for auto-completion) if it's installed
    import argcomplete
except ImportError:
    argcomplete = None


# Set up a console logging handler which just prints messages without any other
# adornments. This will be used for logging messages sent before we "properly"
# configure logging according to the user's preferences
init_i18n()
_CONSOLE = logging.StreamHandler(sys.stderr)
_CONSOLE.setFormatter(logging.Formatter('%(message)s'))
_CONSOLE.setLevel(logging.DEBUG)
logging.getLogger().addHandler(_CONSOLE)


class FileType:
    # Variant of argparse.FileType that handles binary stdin/stdout streams
    # correctly under Python 3
    def __init__(self, mode='r', bufsize=-1, encoding=None, errors=None):
        self._mode = mode
        self._bufsize = bufsize
        self._encoding = encoding
        self._errors = errors

    def __call__(self, string):
        if string == '-':
            if 'r' in self._mode:
                if 'b' in self._mode:
                    try:
                        return sys.stdin.buffer
                    except AttributeError:
                        pass
                return sys.stdin
            elif 'w' in self._mode:
                if 'b' in self._mode:
                    try:
                        return sys.stdout.buffer
                    except AttributeError:
                        pass
                return sys.stdout
            else:
                raise ValueError(_('argument "-" with mode %r') % self._mode)
        try:
            return io.open(string, self._mode, self._bufsize, self._encoding, self._errors)
        except IOError as e:
            raise argparse.ArgumentTypeError(
                    _("can't open '%(name)s': %(error)s") % {'name': string, 'error': e})

    def __repr__(self):
        args = self._mode, self._bufsize
        kwargs = [('encoding', self._encoding), ('errors', self._errors)]
        args_str = ', '.join([repr(arg) for arg in args if arg != -1] +
                             ['%s=%r' % (kw, arg) for kw, arg in kwargs
                              if arg is not None])
        return '%s(%s)' % (type(self).__name__, args_str)


class TerminalApplication:
    """
    Base class for command line applications.

    This class provides command line parsing, file globbing, response file
    handling and common logging configuration for command line utilities.
    Descendent classes should override the main() method to implement their
    main body, and __init__() if they wish to extend the command line options.
    """
    # Get the default output encoding from the default locale
    encoding = locale.getdefaultlocale()[1]

    # This class is the abstract base class for each of the command line
    # utility classes defined. It provides some basic facilities like an option
    # parser, console pretty-printing, logging and exception handling

    def __init__(
            self, version, description=None, config_files=None,
            config_section=None, config_bools=None):
        super(TerminalApplication, self).__init__()
        if description is None:
            description = self.__doc__
        self.parser = argparse.ArgumentParser(
            description=description,
            fromfile_prefix_chars='@')
        self.parser.add_argument(
            '--version', action='version', version=version)
        if config_files:
            self.config = configparser.ConfigParser(interpolation=None)
            self.config_files = config_files
            self.config_section = config_section
            self.config_bools = config_bools
            self.parser.add_argument(
                '-c', '--config', metavar='FILE',
                help=_('specify the configuration file to load'))
        else:
            self.config = None
        self.parser.set_defaults(log_level=logging.WARNING)
        self.parser.add_argument(
            '-q', '--quiet', dest='log_level', action='store_const',
            const=logging.ERROR, help=_('produce less console output'))
        self.parser.add_argument(
            '-v', '--verbose', dest='log_level', action='store_const',
            const=logging.INFO, help=_('produce more console output'))
        opt = self.parser.add_argument(
            '-l', '--log-file', metavar='FILE',
            help=_('log messages to the specified file'))
        if argcomplete:
            # XXX Complete with *.log, *.txt
            #opt.completer = ???
            pass
        self.parser.add_argument(
            '-P', '--pdb', dest='debug', action='store_true', default=False,
            help=_('run under PDB (debug mode)'))

    def __call__(self, args=None):
        if args is None:
            args = sys.argv[1:]
        if argcomplete:
            argcomplete.autocomplete(self.parser, exclude=['-P'])
        elif 'COMP_LINE' in os.environ:
            return 0
        sys.excepthook = self.handle
        args = self.read_configuration(args)
        args = self.parser.parse_args(args)
        self.configure_logging(args)
        if args.debug:
            try:
                import pudb
            except ImportError:
                pudb = None
                import pdb
            return (pudb or pdb).runcall(self.main, args)
        else:
            return self.main(args) or 0

    def read_configuration(self, args):
        if not self.config:
            return args
        # Parse the --config argument only
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('-c', '--config', dest='config', action='store')
        conf_args, args = parser.parse_known_args(args)
        if conf_args.config:
            self.config_files.append(conf_args.config)
        logging.info(
            _('Reading configuration from %s'), ', '.join(self.config_files))
        conf_read = self.config.read(self.config_files)
        if conf_args.config and conf_args.config not in conf_read:
            self.parser.error('unable to read %s' % conf_args.config)
        if conf_read:
            if self.config_bools is None:
                self.config_bools = ['pdb']
            else:
                self.config_bools = ['pdb'] + self.config_bools
            if not self.config_section:
                self.config_section = self.config.sections()[0]
            if not self.config_section in self.config.sections():
                self.parser.error(
                    _('unable to locate [%s] section in configuration') % self.config_section)
            self.parser.set_defaults(**{
                key:
                self.config.getboolean(self.config_section, key)
                if key in self.config_bools else
                self.config.get(self.config_section, key)
                for key in self.config.options(self.config_section)
                })
        return args

    def configure_logging(self, args):
        _CONSOLE.setLevel(args.log_level)
        if args.log_file:
            log_file = logging.FileHandler(args.log_file)
            log_file.setFormatter(
                logging.Formatter('%(asctime)s, %(levelname)s, %(message)s'))
            log_file.setLevel(logging.DEBUG)
            logging.getLogger().addHandler(log_file)
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)

    def handle(self, exc_type, exc_value, exc_trace):
        "Global application exception handler"
        if issubclass(exc_type, (SystemExit,)):
            # Exit with 0 ("success") for system exit (as it was intentional)
            return 0
        elif issubclass(exc_type, (KeyboardInterrupt,)):
            # Exit with 2 if the user deliberately terminates with Ctrl+C
            return 2
        elif issubclass(exc_type, (argparse.ArgumentError,)):
            # For option parser errors output the error along with a message
            # indicating how the help page can be displayed
            logging.critical(str(exc_value))
            logging.critical(_('Try the --help option for more information.'))
            return 2
        elif issubclass(exc_type, (IOError,)):
            # For simple errors like IOError just output the message which
            # should be sufficient for the end user (no need to confuse them
            # with a full stack trace)
            logging.critical(str(exc_value))
            return 1
        else:
            # Otherwise, log the stack trace and the exception into the log
            # file for debugging purposes
            for line in traceback.format_exception(exc_type, exc_value, exc_trace):
                for msg in line.rstrip().split('\n'):
                    logging.critical(msg.replace('%', '%%'))
            return 1

    def main(self, args):
        "Called as the main body of the utility"
        raise NotImplementedError
