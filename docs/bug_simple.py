import time
from sense_emu import SenseHat
import sys

"""
    A bug on a colored background, responding to keypresses.

    Modify the starting state in the `state` dict.
    The background changes colors based on the bug's xy coords.

    This version handles keypresses with a SenseStick object.
"""

state = { "bug_x" : 4,
          "bug_y" : 4,
          "bug_rgb" : (250,250,250) }

sense = SenseHat()

def setscreen():
    """Takes x and y vales and alters screen state"""
    global state
    x = state["bug_x"]
    y = state["bug_y"]
    if sense.low_light:
        zero = 8
    else:
        zero = 48
    brightness = 255 -zero 
    g = int(((x * 32)/255) * brightness + zero)
    b = int(((y * 32)/255) * brightness + zero)
    r = abs(g - b)
    sense.clear((r,g,b))
    #print(r,g,b)

def draw_bug(event):
    global state
    if event.action == 'released':
        # Ignore releases
        return
    elif event.direction == 'up':
        state["bug_x"] = state["bug_x"]
        state["bug_y"] = 7 if state["bug_y"] == 0 else state["bug_y"] - 1
        setscreen()
        sense.set_pixel(state["bug_x"], state["bug_y"], state["bug_rgb"])
    elif event.direction == 'down':
        state["bug_x"] = state["bug_x"]
        state["bug_y"] = 0 if state["bug_y"] == 7 else state["bug_y"] + 1
        setscreen()
        sense.set_pixel(state["bug_x"], state["bug_y"], state["bug_rgb"])
    elif event.direction == 'right':
        state["bug_x"] = 0 if state["bug_x"] == 7 else state["bug_x"] + 1
        state["bug_y"] = state["bug_y"]
        setscreen()
        sense.set_pixel(state["bug_x"], state["bug_y"], state["bug_rgb"])
    elif event.direction == 'left':
        state["bug_x"] = 7 if state["bug_x"] == 0 else state["bug_x"] - 1
        state["bug_y"] = state["bug_y"] 
        setscreen()
        sense.set_pixel(state["bug_x"], state["bug_y"], state["bug_rgb"])

# Initial state
setscreen()
sense.set_pixel(state["bug_x"], state["bug_y"], state["bug_rgb"])

try:
    while True:
        for event in sense.stick.get_events():
            draw_bug(event)
except KeyboardInterrupt:
    sys.exit()

