.. _examples:

========
Examples
========


Introduction
============

The Sense HAT emulator exactly mirrors the official Sense HAT API. The only
difference (required because both the emulator and actual library can be
installed simultaneously on a Pi) is the name: ``sense_emu`` instead of
``sense_hat``. It is recommended to import the library in the following
manner at the top of your code::

    from sense_emu import SenseHat

Then, when you want to change your code to run on the actual HAT all you need
do is change this line to::

    from sense_hat import SenseHat

To run your scripts under the emulator, first start the emulator application,
then start your script.

Several example scripts, with varying degrees of difficulty, are available from
the :menuselection:`File --> Open example` menu within the emulator. Selecting
an example from this menu will open it in Python's IDLE environment.

.. note::

    The example will be opened directly from the installation. To edit the
    example for your own purposes, use :menuselection:`File --> Save As` in
    IDLE to save the file under your home directory (e.g. :file:`/home/pi`).

A selection of example scripts is given in the following sections.


Temperature
===========

Displays the current temperature reading on the Sense HAT's screen:

.. literalinclude:: ../sense_emu/examples/basic/temperature.py


Humidity
========

Displays the current humidity reading on the Sense HAT's screen:

.. literalinclude:: ../sense_emu/examples/basic/humidity.py


Joystick
========

Scrolls a blip around the Sense HAT's screen in response to joystick motions:

.. literalinclude:: ../sense_emu/examples/intermediate/joystick_loop.py

An alternative way to write this example using the joystick's event handler
attributes is given below:

.. literalinclude:: ../sense_emu/examples/advanced/joystick_events.py


Rainbow
=======

Scrolls a rainbow of colours across the Sense HAT's pixels:

.. literalinclude:: ../sense_emu/examples/intermediate/rainbow.py

