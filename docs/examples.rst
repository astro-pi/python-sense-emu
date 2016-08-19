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


Temperature
===========

Displays the current temperature reading on the Sense HAT's screen:

.. literalinclude:: ../sense_emu/examples/temperature.py


Humidity
========

Displays the current humidity reading on the Sense HAT's screen:

.. literalinclude:: ../sense_emu/examples/humidity.py


Joystick
========

Scrolls a blip around the Sense HAT's screen in response to joystick motions:

.. literalinclude:: ../sense_emu/examples/joystick_loop.py

An alternative way to write this example using the joystick's event handler
attributes is given below:

.. literalinclude:: ../sense_emu/examples/joystick_events.py


Rainbow
=======

Scrolls a rainbow of colours across the Sense HAT's pixels:

.. literalinclude:: ../sense_emu/examples/rainbow.py

