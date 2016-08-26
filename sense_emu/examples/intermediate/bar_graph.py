import numpy as np
from time import sleep
from sense_emu import SenseHat


def clamp(value, min_value, max_value):
    """
    Returns *value* clamped to the range *min_value* to *max_value* inclusive.
    """
    return min(max_value, max(min_value, value))

def scale(value, from_min, from_max, to_min=0, to_max=8):
    """
    Returns *value*, which is expected to be in the range *from_min* to
    *from_max* inclusive, scaled to the range *to_min* to *to_max* inclusive.
    If *value* is not within the expected range, the result is not guaranteed
    to be in the scaled range.
    """
    from_range = from_max - from_min
    to_range = to_max - to_min
    return (((value - from_min) / from_range) * to_range) + to_min

def render_bar(screen, origin, width, height, color):
    """
    Fills a rectangle within *screen* based at *origin* (an ``(x, y)`` tuple),
    *width* pixels wide and *height* pixels high. The rectangle will be filled
    in *color*.
    """
    # Calculate the coordinates of the boundaries
    x1, y1 = origin
    x2 = x1 + width
    y2 = y1 + height
    # Invert the Y-coords so we're drawing bottom up
    max_y, max_x = screen.shape[:2]
    y1, y2 = max_y - y2, max_y - y1
    # Draw the bar
    screen[y1:y2, x1:x2, :] = color

def display_readings(hat):
    """
    Display the temperature, pressure, and humidity readings of the HAT as red,
    green, and blue bars on the screen respectively.
    """
    # Calculate the environment values in screen coordinates
    temperature_range = (0, 40)
    pressure_range = (950, 1050)
    humidity_range = (0, 100)
    temperature = scale(clamp(hat.temperature, *temperature_range), *temperature_range)
    pressure = scale(clamp(hat.pressure, *pressure_range), *pressure_range)
    humidity = scale(clamp(hat.humidity, *humidity_range), *humidity_range)
    # Render the bars
    screen = np.zeros((8, 8, 3), dtype=np.uint8)
    render_bar(screen, (0, 0), 2, round(temperature), color=(255, 0, 0))
    render_bar(screen, (3, 0), 2, round(pressure), color=(0, 255, 0))
    render_bar(screen, (6, 0), 2, round(humidity), color=(0, 0, 255))
    hat.set_pixels([pixel for row in screen for pixel in row])


hat = SenseHat()
while True:
    display_readings(hat)
    sleep(0.1)
