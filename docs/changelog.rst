.. _changelog:

==========
Change log
==========


Release 1.2 (2021-09-03)
========================

* Updated code to work with later Gtk3 versions
* Added configuration option for the editor launched for examples


Release 1.1 (2018-07-07)
========================

* Enforce a minimum width of window to ensure orientation sliders are never
  excessively small (`#9`_)
* Various documentation updates (`#12`_ etc.)
* Resizing of the display for high-resolution displays (`#14`_)
* Orientation sliders had no effect when world simulation was disabled (`#19`_)
* When the emulator was spawned by instantiating ``SenseHat()`` in an
  interpreter, pressing Ctrl+C in the interpreter would affect the emulator
  (`#22`_)
* Make :program:`sense_rec` interval configurable (`#24`_)

Many thanks to everyone who reported bugs and provided patches!

.. _#9: https://github.com/RPi-Distro/python-sense-emu/issues/9
.. _#12: https://github.com/RPi-Distro/python-sense-emu/issues/12
.. _#14: https://github.com/RPi-Distro/python-sense-emu/issues/14
.. _#19: https://github.com/RPi-Distro/python-sense-emu/issues/19
.. _#22: https://github.com/RPi-Distro/python-sense-emu/issues/22
.. _#24: https://github.com/RPi-Distro/python-sense-emu/issues/24


Release 1.0 (2016-08-31)
========================

* Initial release
