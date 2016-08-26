import numpy as np
from time import sleep
from sense_emu import SenseHat


def clamp(value, min_value, max_value):
    """
    Returns *value* clamped to the range *min_value* to *max_value* inclusive.
    """
    return min(max_value, max(min_value, value))

def scale(value, from_min, from_max, to_min=0, to_max=7):
    """
    Returns *value*, which is expected to be in the range *from_min* to
    *from_max* inclusive, scaled to the range *to_min* to *to_max* inclusive.
    If *value* is not within the expected range, the result is not guaranteed
    to be in the scaled range.
    """
    from_range = from_max - from_min
    to_range = to_max - to_min
    return (((value - from_min) / from_range) * to_range) + to_min

def display_readings(hat):
    """
    Display the temperature, pressure, and humidity readings of the HAT as red,
    green, and blue bars on the screen respectively.
    """
    temperature_range = (0, 40)
    pressure_range = (950, 1050)
    humidity_range = (0, 100)
    temperature = 7 - round(scale(clamp(hat.temperature, *temperature_range), *temperature_range))
    pressure = 7 - round(scale(clamp(hat.pressure, *pressure_range), *pressure_range))
    humidity = 7 - round(scale(clamp(hat.humidity, *humidity_range), *humidity_range))
    # Scroll screen 1 pixel left, clear the right column, and render new points
    screen = np.array(hat.get_pixels(), dtype=np.uint8).reshape((8, 8, 3))
    screen[:, :-1, :] = screen[:, 1:, :]
    screen[:, 7, :] = (0, 0, 0)
    screen[temperature, 7, :] += np.array((255, 0, 0), dtype=np.uint8)
    screen[pressure, 7, :] += np.array((0, 255, 0), dtype=np.uint8)
    screen[humidity, 7, :] += np.array((0, 0, 255), dtype=np.uint8)
    hat.set_pixels([pixel for row in screen for pixel in row])


hat = SenseHat()
hat.clear()
while True:
    display_readings(hat)
    sleep(1)
