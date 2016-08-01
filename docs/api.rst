.. _api:

=============
Sense HAT API
=============

.. module:: sense_emu

The main class which is used to interact with the Sense HAT emulator is
:class:`SenseHat`. This provides accesss to all sensors, the LED pixel display,
and the joystick. It is recommended that you import the library using the
following idiom::

    from sense_emu import SenseHat

This way, when you wish to deploy your code on an actual Sense HAT the only
change you need to make is to this line, changing it to::

    from sense_hat import SenseHat

SenseHat
========

.. autoclass:: SenseHat
    :members:

SenseStick
==========

.. autoclass:: SenseStick
    :members:

InputEvent
==========

.. autoclass:: InputEvent
    :members:

Constants
=========

.. data:: DIRECTION_UP
.. data:: DIRECTION_DOWN
.. data:: DIRECTION_LEFT
.. data:: DIRECTION_RIGHT
.. data:: DIRECTION_MIDDLE

    Constants representating the direction in which the joystick has been
    pushed. :data:`DIRECTION_MIDDLE` refers to pressing the joystick as a
    button.

.. data:: ACTION_PRESSED
.. data:: ACTION_RELEASED
.. data:: ACTION_HELD

    Constants representing the actions that can be applied to the joystick.

