# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Raspberry Pi Sense HAT Emulator library for the Raspberry Pi
# Copyright (c) 2016 Raspberry Pi Foundation <info@raspberrypi.org>
#
# All Rights Reserved.

from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )


def clamp(value, min_value, max_value):
    """
    Return *value* clipped to the range *min_value* to *max_value* inclusive.
    """
    return min(max_value, max(min_value, value))

