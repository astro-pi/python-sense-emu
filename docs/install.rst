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
so. To install using apt simply:

.. code-block:: console

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
apt's normal upgrade procedure:

.. code-block:: console

    $ sudo apt-get update
    $ sudo apt-get upgrade

If you ever need to remove your installation:

.. code-block:: console

    $ sudo apt-get remove python-sense-emu python3-sense-emu sense-emu-tools


.. _ubuntu_install:

Ubuntu installation
===================

To install from the author's `PPA`_:

.. code-block:: console

    $ sudo add-apt-repository ppa://waveform/ppa
    $ sudo apt-get update
    $ sudo apt-get install python-sense-emu python3-sense-emu sense-emu-tools

To upgrade your installation when new releases are made you can simply use
apt's normal upgrade procedure:

.. code-block:: console

    $ sudo apt-get update
    $ sudo apt-get upgrade

To remove the installation:

.. code-block:: console

    $ sudo apt-get remove python-sense-emu python3-sense-emu sense-emu-tools


.. _macos_install:

macOS installation
==================

The following installation instructions assume you are using `Homebrew`_ as
your macOS package manager:

.. code-block:: console

    $ brew install pygobject3 gtk+3

If you are using Python virtual environments for the Sense HAT Emulator, the
``system-site-packages`` option must be enabled within the virtualenv.

For existing virtual environments:

.. code-block:: console

    $ rm ${VIRTUAL_ENV}/lib/python*/no-global-site-packages.txt

For new virtual environments:

.. code-block:: console

    $ virtualenv --system-site-packages

Activate your virtual environment and install the Sense HAT Emulator:

.. code-block:: console

    $ pip install sense-emu


.. _other_install:

Alternate platforms
===================

On platforms other than Raspbian or Ubuntu, it is probably simplest to install
system wide using Python's ``pip`` tool:

.. code-block:: console

    $ pip install sense-emu

To upgrade your installation when new releases are made:

.. code-block:: console

    $ pip install -U sense-emu

If you ever need to remove your installation:

.. code-block:: console

    $ pip uninstall sense-emu

.. note::

    The emulator application requires PyGObject and cairo to be installed (GTK3
    bindings for Python), but this cannot be obtained from PyPI; install
    PyGObject manually from your operating system's package manager (e.g.
    python-gi, python3-gi, python-gi-cairo, and python3-gi-cairo on
    Raspbian/Ubuntu).

    Also note that installation via ``pip`` won't create short-cuts for the
    emulator application in your desktop's start menu. Instead you will have to
    launch it manually by running ``sense_emu_gui`` from the command line.


.. _Homebrew: http://brew.sh/
.. _Raspbian: http://www.raspbian.org/
.. _PPA: https://launchpad.net/~waveform/+archive/ppa
