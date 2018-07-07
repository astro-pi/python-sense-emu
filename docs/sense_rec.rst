.. _sense_rec:

=========
sense_rec
=========

Records sensor readings from the Raspberry Pi Sense HAT in real time,
outputting the results to a file for later playback or analysis. This is most
useful for preparing records of experiments for use with the Sense HAT
emulator. For example, a recording of a Sense HAT being dropped, a recording of
a `HAB`_ flight, a recording of the cycle of temperature over a few days, etc.

Synopsis
========

.. code-block:: text

    sense_rec [-h] [--version] [-q] [-v] [-l FILE] [-P] [-c CONFIG]
              [-d DURATION] [-f] output

Description
===========

.. program:: sense_rec

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

.. option:: -c FILE, --config FILE

    the Sense HAT configuration file to use (default:
    :file:`/etc/RTIMULib.ini`)

.. option:: -d SECS, --duration SECS

    the duration to record for in seconds (default: record until terminated
    with :kbd:`Control-C`)

.. option:: -i SECS, --interval SECS

    the delay between each reading in seconds (default: the IMU polling
    interval, typically 0.003 seconds)

.. option:: -f, --flush

    flush every record to disk immediately; reduces chances of truncated data
    on power loss, but greatly increases disk activity


Examples
========

To record an experiment with the Sense HAT, simply execute :program:`sense_rec`
with the filename you wish to record the results:

.. code-block:: console

    $ sense_rec experiment.hat

By default, the recording will continue indefinitely. Press :kbd:`Control-C`
to terminate the recording. If you want to record for a specific duration,
you can use the :option:`--duration` option to specify the number of seconds:

.. code-block:: console

    $ sense_rec --duration 10 short_experiment.hat

This tool can be run simultaneously with scripts that use the Sense HAT. Simply
start your script in one terminal, then open another to start
:program:`sense_rec`. Alternatively, you can use the shell's job control
facilities to start recording in the background:

.. code-block:: console

    $ sense_rec experiment.hat &
    $ python experiment.py
    ...
    $ kill %1

.. warning::

    Be aware that other scripts attempting to use the HAT's sensors will
    likely obtain different readings than they would have if run standalone.
    Some of the HAT's sensors are affected by their query-rate, and
    :program:`sense_rec` drives all sensors at close to their maximum rate.

If :file:`-` is specified as the output file, :program:`sense_rec` will write
its output to stdout. This can be used to reduce the disk space required for
long output by piping the output through a compression tool like
:program:`gzip`:

.. code-block:: console

    $ sense_rec - | gzip -c - > experiment.hat.gz

When compressed in this manner the data typically uses approximately 3Kb per
second (without :program:`gzip` the recording will use approximately 10Kb of
disk space per second). Use :program:`gunzip` to de-compress the data for
playback or analysis:

.. code-block:: console

    $ gunzip -c experiment.hat.gz | sense_play -

Another method of reducing the data usage is increasing the interval between
readings (the default is the IMU polling interval which is an extremely short
3ms). Obviously a longer interval will reduce the "fidelity" of the recording;
you will only see the sensors update at each interval during playback, however
it can be extremely useful for very long recordings. For example, to record
with a 1 second interval between readings for 24 hours:

.. code-block:: console

    $ sense_rec -i 1 -d $((24*60*60)) one_day_experiment.hat

Finally, you can use pipes in conjunction with :program:`sense_csv` to
produce CSV output directly:

.. code-block:: console

    $ sense_rec - | sense_csv - experiment.csv

Be warned that CSV data is substantially larger than the binary format (CSV
data uses approximately 25Kb per second at the default interval).

.. _HAB: https://en.wikipedia.org/wiki/High-altitude_balloon
