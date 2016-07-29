.. _install:

============
Installation
============


.. _raspbian_install:

Raspbian installation
=====================

If you are using the `Raspbian`_ distro, it is best to install the Sense HAT
Emulator using the system's package manager: apt. This will ensure that the
emulator is easy to keep up to date, and easy to remove should you wish to do
so. To install using apt simply::

    $ sudo apt-get update
    $ sudo apt-get install python-sense-emu python3-sense-emu sense-emu-tools

These three packages contain the following things:

sense-emu-tools
  This package contains the Sense HAT Emulator application.

python-sense-emu
  This is the Python 2 version of the Sense HAT Emulator library.

python3-sense-emu
  This is the Python 3 version of the Sense HAT Emulator library.

To upgrade your installation when new releases are made you can simply use
apt's normal upgrade procedure::

    $ sudo apt-get update
    $ sudo apt-get upgrade

If you ever need to remove your installation::

    $ sudo apt-get remove python-sense-emu python3-sense-emu sense-emu-tools

.. _Raspbian: http://www.raspbian.org/


.. _ubuntu_install:

Ubuntu installation
===================

To install from the author's `PPA`_::

    $ sudo add-apt-repository ppa://waveform/ppa
    $ sudo apt-get update
    $ sudo apt-get install python-sense-emu python3-sense-emu sense-emu-tools

To upgrade your installation when new releases are made you can simply use
apt's normal upgrade procedure::

    $ sudo apt-get update
    $ sudo apt-get upgrade

To remove the installation::

    $ sudo apt-get remove python-sense-emu python3-sense-emu sense-emu-tools

.. _PPA: https://launchpad.net/~waveform/+archive/ppa


.. _other_install:

Alternate platforms
===================

On platforms other than Raspbian or Ubuntu, it is probably simplest to install
system wide using Python's ``pip`` tool::

    $ pip install sense-emu

To upgrade your installation when new releases are made::

    $ pip install -U sense-emu

If you ever need to remove your installation::

    $ pip uninstall sense-emu

.. note::

    The emulator application requires PyGObject to be installed (GTK3 bindings
    for Python), but this cannot be obtained from PyPI; install PyGObject
    manually from your operating system's package manager (e.g. python-gi or
    python3-gi on Raspbian/Ubuntu).

    Also note that installation via ``pip`` won't create short-cuts for the
    emulator application in your desktop's start menu. Instead you will have to
    launch it manually by running ``sense_emu_gui`` from the command line.

