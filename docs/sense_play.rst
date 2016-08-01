.. _sense_play:

==========
sense_play
==========

Replays readings recorded from a Raspberry Pi Sense HAT, via the Sense HAT
emulation library.

Synopsis
========

::

    sense_play [-h] [--version] [-q] [-v] [-l FILE] [-P] input

Description
===========

.. program:: sense_play

.. option:: -h, --help

    show this help message and exit

.. option:: --version

    show this program's version number and exit

.. option:: -q, --quiet

    produce less console output

.. option:: -v, --verbose

    produce more console output

.. option:: -l FILE, --log-file FILE

    log messages to the specified file

.. option:: -P, --pdb

    run under PDB (debug mode)


Examples
========

To play back an experiment recorded from the Sense HAT, simply execute
:program:`sense_play` with the filename you wish to play back::

    $ sense_play experiment.hat

Playback will start immediately and continue in real-time (at the recording
rate) until the file is exhausted. If you wish to start an emulated script
at the same time as playback, you can use the shell's job control facilities::

    $ sense_play experiment.hat & python experiment.py

If :file:`-` is specified as the input file, :program:`sense_play` will read
its from stdin. This can be used to play back compressed recordings (see
Examples under :program:`sense_rec`) without using any disk space for
decompression::

    $ gunzip -c experiment.hat.gz | sense_play -

.. note::

    If playback is going too slowly (e.g. because the Pi is too busy with other
    tasks, or because the data cannot be read quickly enough from the SD card),
    :program:`sense_play` will skip records and print a warning to the console
    at the end of playback with the number of records skipped.

