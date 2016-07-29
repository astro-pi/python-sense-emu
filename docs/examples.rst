.. _examples:

========
Examples
========


Introduction
============

The Sense HAT emulator exactly mirrors the official Sense HAT API. The only
difference (required because both the emulator and actual library can be
installed simultaneously on a Pi) is the name: ``sense_emu`` instead of
``sense_hat``. It is recommended to import the library in the following
manner at the top of your code::

    from sense_emu import SenseHat

Then, when you want to change your code to run on the actual HAT all you need
do is change this line to::

    from sense_hat import SenseHat

To run your scripts under the emulator, first start the emulator application,
then start your script.


Temperature
===========

Displays the current temperature reading on the Sense HAT's screen::

    from sense_emu import SenseHat

    sense = SenseHat()

    red = (255, 0, 0)
    blue = (0, 0, 255)

    while True:
        temp = sense.temp
        pixels = [red if i < temp else blue for i in range(64)]
        sense.set_pixels(pixels)


Humidity
========

Displays the current humidity reading on the Sense HAT's screen::

    from sense_emu import SenseHat

    sense = SenseHat()

    green = (0, 255, 0)
    white = (255, 255, 255)

    while True:
        humidity = sense.humidity
        humidity_value = 64 * humidity / 100

        pixels = [green if i < humidity_value else white for i in range(64)]

        sense.set_pixels(pixels)


Joystick
========

Scrolls a blip around the Sense HAT's screen in response to joystick motions::

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


Rainbow
=======

Scrolls a rainbow of colours across the Sense HAT's pixels::

    from sense_emu import SenseHat

    sense = SenseHat()

    pixels = [
        [255, 0, 0], [255, 0, 0], [255, 87, 0], [255, 196, 0], [205, 255, 0], [95, 255, 0], [0, 255, 13], [0, 255, 122],
        [255, 0, 0], [255, 96, 0], [255, 205, 0], [196, 255, 0], [87, 255, 0], [0, 255, 22], [0, 255, 131], [0, 255, 240],
        [255, 105, 0], [255, 214, 0], [187, 255, 0], [78, 255, 0], [0, 255, 30], [0, 255, 140], [0, 255, 248], [0, 152, 255],
        [255, 223, 0], [178, 255, 0], [70, 255, 0], [0, 255, 40], [0, 255, 148], [0, 253, 255], [0, 144, 255], [0, 34, 255],
        [170, 255, 0], [61, 255, 0], [0, 255, 48], [0, 255, 157], [0, 243, 255], [0, 134, 255], [0, 26, 255], [83, 0, 255],
        [52, 255, 0], [0, 255, 57], [0, 255, 166], [0, 235, 255], [0, 126, 255], [0, 17, 255], [92, 0, 255], [201, 0, 255],
        [0, 255, 66], [0, 255, 174], [0, 226, 255], [0, 117, 255], [0, 8, 255], [100, 0, 255], [210, 0, 255], [255, 0, 192],
        [0, 255, 183], [0, 217, 255], [0, 109, 255], [0, 0, 255], [110, 0, 255], [218, 0, 255], [255, 0, 183], [255, 0, 74]
    ]


    def next_colour(pix):
        r = pix[0]
        g = pix[1]
        b = pix[2]

        if (r == 255 and g < 255 and b == 0):
            g += 1

        if (g == 255 and r > 0 and b == 0):
            r -= 1

        if (g == 255 and b < 255 and r == 0):
            b += 1

        if (b == 255 and g > 0 and r == 0):
            g -= 1

        if (b == 255 and r < 255 and g == 0):
            r += 1

        if (r == 255 and b > 0 and g == 0):
            b -= 1

        pix[0] = r
        pix[1] = g
        pix[2] = b

    while True:
        for pix in pixels:
            next_colour(pix)

        sense.set_pixels(pixels)
