# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Raspberry Pi Sense HAT Emulator library for the Raspberry Pi
# Copyright (c) 2016 Raspberry Pi Foundation <info@raspberrypi.org>
#
# All Rights Reserved.

# vim: set fileencoding=utf-8:

from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )
str = type('')


# Backported from py3.4
def mean(data):
    if iter(data) is data:
        data = list(data)
    n = len(data)
    if not n:
        raise ValueError('cannot calculate mean of empty data')
    return sum(data) / n


# Backported from py3.4
def median(data):
    data = sorted(data)
    n = len(data)
    if not n:
        raise ValueError('cannot calculate median of empty data')
    elif n % 2:
        return data[n // 2]
    else:
        i = n // 2
        return (data[i - 1] + data[i]) / 2

