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
str = type('')


import math
from functools import total_ordering
from collections import namedtuple, Sequence
try:
    from itertools import zip_longest, islice, tee
except ImportError:
    # Py2 compat
    from itertools import izip_longest as zip_longest, islice, tee


class Vector(namedtuple('Vector', ('x', 'y', 'z'))):
    """
    Represents a 3-dimensional vector.

    This :func:`~collections.namedtuple` derivative represents a 3-dimensional
    vector with :attr:`x`, :attr:`y`, :attr:`z` components. Instances can be
    constructed in a number of ways: by explicitly specifying the x, y, and z
    components (optionally with keyword identifiers), or leaving them empty to
    default to 0::

        >>> Vector(1, 1, 1)
        Vector(x=1, y=1, z=1)
        >>> Vector(x=2, y=0, z=0)
        Vector(x=2, y=0, z=0)
        >>> Vector()
        Vector(x=0, y=0, z=0)
        >>> Vector(y=10)
        Vector(x=0, y=10, z=0)

    Shortcuts are available for vectors representing the X, Y, and Z axes::

        >>> X
        Vector(x=1, y=0, z=0)
        >>> Y
        Vector(x=0, y=1, z=0)

    Note that vectors don't much care whether their components are integers,
    floating point values, or ``None``::

        >>> Vector(1.0, 1, 1)
        Vector(x=1.0, y=1, z=1)
        >>> Vector(2, None, None)
        Vector(x=2, y=None, z=None)

    The class supports simple arithmetic operations with other vectors such as
    addition and subtraction, along with multiplication and division, raising
    to powers, bit-shifting, and so on. Such operations are performed
    element-wise [1]_::

        >>> v1 = Vector(1, 1, 1)
        >>> v2 = Vector(2, 2, 2)
        >>> v1 + v2
        Vector(x=3, y=3, z=3)
        >>> v1 * v2
        Vector(x=2, y=2, z=2)

    Simple arithmetic operations with scalars return a new vector with that
    operation performed on all elements of the original. For example::

        >>> v = Vector()
        >>> v
        Vector(x=0, y=0, z=0)
        >>> v + 1
        Vector(x=1, y=1, z=1)
        >>> 2 * (v + 2)
        Vector(x=4, y=4, z=4)
        >>> Vector(y=2) ** 2
        Vector(x=0, y=4, z=0)

    .. note::

        Note that, as a derivative of :func:`~collections.namedtuple`,
        instances of this class are immutable. That is, you cannot directly
        manipulate the :attr:`x`, :attr:`y`, and :attr:`z` attributes; instead
        you must create a new vector (for example, by adding two vectors
        together). The advantage of this is that vector instances can be
        members of a :class:`set` or keys in a :class:`dict`.

    .. [1] I realize math purists will hate this (and demand that abs() should
       be magnitude and * should invoke matrix multiplication), but the
       element wise operations are sufficiently useful to warrant the
       short-hand syntax.

    .. automethod:: replace

    .. automethod:: ceil

    .. automethod:: floor

    .. automethod:: dot

    .. automethod:: cross

    .. automethod:: distance_to

    .. automethod:: angle_between

    .. automethod:: project

    .. automethod:: rotate

    .. attribute:: x

        The position or length of the vector along the X-axis.

    .. attribute:: y

        The position or length of the vector along the Y-axis.

    .. attribute:: z

        The position or length of the vector along the Z-axis.

    .. autoattribute:: magnitude

    .. autoattribute:: unit
    """

    __slots__ = ()

    def __new__(cls, x=0, y=0, z=0):
        return super(Vector, cls).__new__(cls, x, y, z)

    @classmethod
    def from_string(cls, s, type=int):
        x, y, z = s.split(',')
        return cls(type(x), type(y), type(z))

    @property
    def __dict__(self):
        # This is required to work around a subtle issue encountered in Python
        # 3.3 and above. In these versions (probably deliberately), the
        # __dict__ property is not inherited by namedtuple descendents
        return super(Vector, self).__dict__

    def __str__(self):
        return '%s,%s,%s' % (self.x, self.y, self.z)

    def __add__(self, other):
        try:
            return Vector(self.x + other.x, self.y + other.y, self.z + other.z)
        except AttributeError:
            return Vector(self.x + other, self.y + other, self.z + other)

    __radd__ = __add__

    def __sub__(self, other):
        try:
            return Vector(self.x - other.x, self.y - other.y, self.z - other.z)
        except AttributeError:
            return Vector(self.x - other, self.y - other, self.z - other)

    def __mul__(self, other):
        try:
            return Vector(self.x * other.x, self.y * other.y, self.z * other.z)
        except AttributeError:
            return Vector(self.x * other, self.y * other, self.z * other)

    __rmul__ = __mul__

    def __truediv__(self, other):
        try:
            return Vector(self.x / other.x, self.y / other.y, self.z / other.z)
        except AttributeError:
            return Vector(self.x / other, self.y / other, self.z / other)

    def __floordiv__(self, other):
        try:
            return Vector(self.x // other.x, self.y // other.y, self.z // other.z)
        except AttributeError:
            return Vector(self.x // other, self.y // other, self.z // other)

    def __mod__(self, other):
        try:
            return Vector(self.x % other.x, self.y % other.y, self.z % other.z)
        except AttributeError:
            return Vector(self.x % other, self.y % other, self.z % other)

    def __pow__(self, other, modulo=None):
        if modulo is not None:
            try:
                # XXX What about other vector, modulo scalar, and other scalar, modulo vector?
                return Vector(
                        pow(self.x, other.x, modulo.x),
                        pow(self.y, other.y, modulo.y),
                        pow(self.z, other.z, modulo.z))
            except AttributeError:
                return Vector(
                        pow(self.x, other, modulo),
                        pow(self.y, other, modulo),
                        pow(self.z, other, modulo))
        try:
            return Vector(
                    pow(self.x, other.x),
                    pow(self.y, other.y),
                    pow(self.z, other.z))
        except AttributeError:
            return Vector(
                    pow(self.x, other),
                    pow(self.y, other),
                    pow(self.z, other))

    def __lshift__(self, other):
        try:
            return Vector(self.x << other.x, self.y << other.y, self.z << other.z)
        except AttributeError:
            return Vector(self.x << other, self.y << other, self.z << other)

    def __rshift__(self, other):
        try:
            return Vector(self.x >> other.x, self.y >> other.y, self.z >> other.z)
        except AttributeError:
            return Vector(self.x >> other, self.y >> other, self.z >> other)

    def __and__(self, other):
        try:
            return Vector(self.x & other.x, self.y & other.y, self.z & other.z)
        except AttributeError:
            return Vector(self.x & other, self.y & other, self.z & other)

    def __xor__(self, other):
        try:
            return Vector(self.x ^ other.x, self.y ^ other.y, self.z ^ other.z)
        except AttributeError:
            return Vector(self.x ^ other, self.y ^ other, self.z ^ other)

    def __or__(self, other):
        try:
            return Vector(self.x | other.x, self.y | other.y, self.z | other.z)
        except AttributeError:
            return Vector(self.x | other, self.y | other, self.z | other)

    def __neg__(self):
        return Vector(-self.x, -self.y, -self.z)

    def __pos__(self):
        return self

    def __abs__(self):
        return Vector(abs(self.x), abs(self.y), abs(self.z))

    def __bool__(self):
        return bool(self.x or self.y or self.z)

    def __trunc__(self):
        return Vector(math.trunc(self.x), math.trunc(self.y), math.trunc(self.z))

    # Py2 compat
    __nonzero__ = __bool__
    __div__ = __truediv__

    def replace(self, x=None, y=None, z=None):
        """
        Return the vector with the x, y, or z axes replaced with the specified
        values. For example::

            >>> Vector(1, 2, 3).replace(z=4)
            Vector(x=1, y=2, z=4)
        """
        return Vector(
            self.x if x is None else x,
            self.y if y is None else y,
            self.z if z is None else z)

    def floor(self):
        """
        Return the vector with the floor of each component. This is only useful
        for vectors containing floating point components::

            >>> Vector(0.5, -0.5, 1.9)
            Vector(0.0, -1.0, 1.0)
        """
        return Vector(
            int(math.floor(self.x)),
            int(math.floor(self.y)),
            int(math.floor(self.z)))

    def ceil(self):
        """
        Return the vector with the ceiling of each component. This is only
        useful for vectors containing floating point components::

            >>> Vector(0.5, -0.5, 1.2)
            Vector(1.0, 0.0, 2.0)
        """
        return Vector(
            int(math.ceil(self.x)),
            int(math.ceil(self.y)),
            int(math.ceil(self.z)))

    def round(self, ndigits=0):
        """
        Return the vector with the rounded value of each component. This is
        only useful for vectors containing floating point components::

            >>> Vector(0.5, -0.5, 1.2)
            Vector(1.0, -1.0, 1.0)

        The *ndigits* argument operates as it does in the built-in
        :func:`round` function, specifying the number of decimal (or integer)
        places to round to.
        """
        if ndigits <= 0:
            return Vector(
                int(round(self.x, ndigits)),
                int(round(self.y, ndigits)),
                int(round(self.z, ndigits)))
        else:
            return Vector(
                round(self.x, ndigits),
                round(self.y, ndigits),
                round(self.z, ndigits))

    def dot(self, other):
        """
        Return the `dot product`_ of the vector with the *other* vector. The
        result is a scalar value. For example::

            >>> Vector(1, 2, 3).dot(Vector(2, 2, 2))
            12
            >>> Vector(1, 2, 3).dot(X)
            1

        .. _dot product: http://en.wikipedia.org/wiki/Dot_product
        """
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other):
        """
        Return the `cross product`_ of the vector with the *other* vector. The
        result is another vector. For example::

            >>> Vector(1, 2, 3).cross(Vector(2, 2, 2))
            Vector(x=-2, y=4, z=-2)
            >>> Vector(1, 2, 3).cross(X)
            Vector(x=0, y=3, z=-2)

        .. _cross product: http://en.wikipedia.org/wiki/Cross_product
        """
        return Vector(
                self.y * other.z - self.z * other.y,
                self.z * other.x - self.x * other.z,
                self.x * other.y - self.y * other.x)

    def distance_to(self, other):
        """
        Return the Euclidian distance between two three dimensional points
        (represented as vectors), calculated according to `Pythagoras'
        theorem`_. For example::

            >>> Vector(1, 2, 3).distance_to(Vector(2, 2, 2))
            1.4142135623730951
            >>> O.distance_to(X)
            1.0

        .. _Pythagoras' theorem: http://en.wikipedia.org/wiki/Pythagorean_theorem
        """
        return (other - self).magnitude

    def angle_between(self, other):
        """
        Returns the angle between this vector and the *other* vector on a plane
        that contains both vectors. The result is measured in degrees. For
        example::

            >>> X.angle_between(Y)
            90.0
            >>> (X + Y).angle_between(X)
            45.00000000000001
        """
        return math.degrees(math.acos(self.unit.dot(other.unit)))

    def project(self, other):
        """
        Return the `scalar projection`_ of this vector onto the *other* vector.
        This is a scalar indicating the length of this vector in the direction
        of the *other* vector. For example::

            >>> Vector(1, 2, 3).project(2 * Y)
            2.0
            >>> Vector(3, 4, 5).project(Vector(3, 4, 0))
            5.0

        .. _scalar projection: https://en.wikipedia.org/wiki/Scalar_projection
        """
        return self.dot(other.unit)

    def rotate(self, angle, about, origin=None):
        """
        Return this vector after `rotation`_ of *angle* degrees about the line
        passing through *origin* in the direction *about*. Origin defaults to
        the vector 0, 0, 0. Hence, if this parameter is omitted this method
        calculates rotation about the axis (through the origin) defined by
        *about*.  For example::

            >>> Y.rotate(90, about=X)
            Vector(x=0, y=6.123233995736766e-17, z=1.0)
            >>> Vector(3, 4, 5).rotate(30, about=X, origin=10 * Y)
            Vector(x=3.0, y=2.3038475772933684, z=1.330127018922194)

        Information about rotation around arbitrary lines was obtained from
        `Glenn Murray's informative site`_.

        .. _rotation: https://en.wikipedia.org/wiki/Rotation_group_SO%283%29
        .. _Glenn Murray's informative site: http://inside.mines.edu/fs_home/gmurray/ArbitraryAxisRotation/
        """
        r = math.radians(angle)
        sin = math.sin(r)
        cos = math.cos(r)
        x, y, z = self
        if origin is None:
            # Fast-paths: rotation about a specific unit axis
            if about == X:
                return Vector(x, y * cos - z * sin, y * sin + z * cos)
            elif about == Y:
                return Vector(z * sin + x * cos, y, z * cos - x * sin)
            elif about == Z:
                return Vector(x * cos - y * sin, x * sin + y * cos, z)
            elif about == negX:
                return Vector(x, y * cos + z * sin, z * cos - y * sin)
            elif about == negY:
                return Vector(x * cos - z * sin, y, z * cos + x * sin)
            elif about == negZ:
                return Vector(x * cos + y * sin, y * cos - x * sin, z)
            # Rotation about an arbitrary axis
            u, v, w = about.unit
            return Vector(
                u * (u * x + v * y + w * z) * (1 - cos) + x * cos + (-w * y + v * z) * sin,
                v * (u * x + v * y + w * z) * (1 - cos) + y * cos + ( w * x - u * z) * sin,
                w * (u * x + v * y + w * z) * (1 - cos) + z * cos + (-v * x + u * y) * sin)
        # Rotation about an arbitrary line
        a, b, c = origin
        u, v, w = about.unit
        return Vector(
            (a * (v ** 2 + w ** 2) - u * (b * v + c * w - u * x - v * y - w * z)) * (1 - cos) + x * cos + (-c * v + b * w - w * y + v * z) * sin,
            (b * (u ** 2 + w ** 2) - v * (a * u + c * w - u * x - v * y - w * z)) * (1 - cos) + y * cos + ( c * u - a * w + w * x - u * z) * sin,
            (c * (u ** 2 + v ** 2) - w * (a * u + b * v - u * x - v * y - w * z)) * (1 - cos) + z * cos + (-b * u + a * v - v * x + u * y) * sin)

    @property
    def magnitude(self):
        """
        Returns the magnitude of the vector. This could also be considered the
        distance of the vector from the origin, i.e. ``v.magnitude`` is
        equivalent to ``Vector().distance_to(v)``. For example::

            >>> Vector(2, 4, 4).magnitude
            6.0
            >>> Vector().distance_to(Vector(2, 4, 4))
            6.0
        """
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    @property
    def unit(self):
        """
        Return a `unit vector`_ (a vector with a magnitude of one) with the
        same direction as this vector::

            >>> X.unit
            Vector(x=1.0, y=0.0, z=0.0)
            >>> (2 * Y).unit
            Vector(x=0.0, y=1.0, z=0.0)

        .. note::

            If the vector's magnitude is zero, this property returns the
            original vector.

        .. _unit vector: http://en.wikipedia.org/wiki/Unit_vector
        """
        try:
            return self / self.magnitude
        except ZeroDivisionError:
            return self


# Short-hand variants
V = Vector
O = V()
X = V(x=1)
Y = V(y=1)
Z = V(z=1)
# These aren't exposed as short-hands; they're only pre-calculated here to
# speed up the fast-paths in the rotate() method
negX = V(x=-1)
negY = V(y=-1)
negZ = V(z=-1)

