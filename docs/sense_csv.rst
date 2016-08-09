.. _sense_csv:

=========
sense_csv
=========

Converts a Sense HAT recording to CSV format, for the purposes of debugging or
analysis.

Synopsis
========

::

    sense_csv [-h] [--version] [-q] [-v] [-l FILE] [-P]
              [--timestamp-format TIMESTAMP_FORMAT] [--header] input output

Description
===========

.. program:: sense_csv

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

.. option:: --timestamp-format FMT

    the format to use when outputting the record timestamp (default: ISO8601
    format, which is "%Y-%m-%dT%H:%M:%S.%f"; see :manpage:`strftime(3)` for
    information on valid format parameters)

.. option:: --header

    if specified, output column headers at the start of the output

Examples
========

To convert a recording to CSV, simply run :program:`sense_csv` with the
recorded file as the first filename, and the output CSV file as the second::

    $ sense_csv experiment.hat experiment.csv

By default, only the data is output, with the columns defined as follows:

1. Timestamp - the moment in time at which the readings were taken (note that
   as the Pi lacks a real-time clock, this is likely to be inaccurate unless
   the clock has been set with NTP).

2. Pressure - the reading from the pressure sensor in hectopascals (hPa).

3. Temperature - the temperature reading from the pressure sensor in degrees
   celsius (°C).

4. Humidity - the reading from the humidity sensor in % humidity.

5. Temperature - the temperature reading from the humidity sensor in degrees
   celsius (°C).

6. Accelerometer X-axis - the acceleration reading along the X-axis of the
   HAT in g.

7. Accelerometer Y-axis.

8. Accelerometer Z-axis.

9. Gyroscope X-axis - the angular rate of change around the X-axis of the
   HAT in degrees per second.

10. Gyroscope Y-axis.

11. Gyroscope Z-axis.

12. Compass X-axis - the magnetometer reading along the X-axis in micro-teslas.

13. Compass Y-axis.

14. Compass Z-axis.

15. Orientation X-axis - the computed orientation of the HAT as radians
    rotation (-π to +π) about the X-axis.

16. Orientation Y-axis.

17. Orientation Z-axis.

If you wish to include column headers as the first row of data, simply
specify the :option:`--header` option::

    $ sense_csv --header experiment.hat experiment.csv

If :file:`-` is specified for either filename, :program:`sense_csv` will read
from stdin, or write to stdout. This can be used in conjunction with other
standard command line utilities for all sorts of effects. For example, to
produce a CSV file containing only the timestamps, humidity, and accelerometer
readings::

    $ sense_csv --header experiment.hat - | cut -d, -f1,4,6-8 > experiment.csv

