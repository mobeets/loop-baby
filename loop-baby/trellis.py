import time
import random
from board import SCL, SDA
import busio
from adafruit_neotrellis.neotrellis import NeoTrellis

BUTTON_PRESSED = NeoTrellis.EDGE_RISING
BUTTON_RELEASED = NeoTrellis.EDGE_FALLING

def random_color():
    return (random.randint(0,255), random.randint(0,255), random.randint(0,255))

class Trellis:
    """
    relays button presses by adding them to a queue
    buttons can be referred to by name, index, or color group name
    """
    def __init__(self, startup_color='random', debug=True):

        self.debug = debug
        self.nbuttons = 16
        self.colors = {'off': (0, 0, 0), 'purple': (180, 0, 255),
            'red': (255, 0, 0), 'orange': (255, 164, 0),
            'green': (0, 255, 0), 'yellow': (158, 152, 17),
            'gray': (100, 100, 100),
            'blue': (0, 0, 255),
            'lightblue': (7, 34, 81),
            'blueish': (33, 211, 237),
            'darkgray': (10, 10, 10),
            'seagreen': (30, 255, 30),
            'lightseagreen': (39, 239, 120),
            'salmon': (206, 28, 41),
            'lightorange': (176, 76, 9),
            'lightpurple': (87, 20, 174),
            'lighterpurple': (70, 27, 87),
            'pink': (100, 0, 100)}

        # create the i2c object for the trellis
        self.i2c_bus = busio.I2C(SCL, SDA)

        # create the trellis
        self.trellis = NeoTrellis(self.i2c_bus) # can set interrupt=True here...

        # for handling colors of groups of buttons
        self.startup_color = startup_color
        self.color_map = {}

        # to ensure callback set
        self.button_handler = None

    def set_color_map(self, color_map):
        self.color_map = color_map

    def set_callback(self, fcn):
        # callback for when buttons are pressed
        self.button_handler = fcn
        # set handlers for button press
        self.activate(self.startup_color, lightshow=True)

    def activate(self, startup_color=None, lightshow=False):
        if self.button_handler is None:
            print("Error: callback must be set using 'set_callback'")

        for i in range(self.nbuttons):
            # activate rising edge events on all keys
            self.trellis.activate_key(i, BUTTON_PRESSED)
            # activate falling edge events on all keys
            self.trellis.activate_key(i, BUTTON_RELEASED)
            # set all keys to trigger the blink callback
            self.trellis.callbacks[i] = self.button_handler

            if not lightshow:
                continue
            #cycle the LEDs on startup
            if startup_color is not None:
                if startup_color == 'random':
                    color = random_color()
                else:
                    color = self.colors[startup_color]
                self.trellis.pixels[i] = color
                time.sleep(.03)

        for i in range(self.nbuttons):
            self.trellis.pixels[i] = self.colors['off']
            if lightshow:
                time.sleep(.03)

    def end_lightshow(self, event=None):
        # reset callbacks and turn lights off
        if event is None or event.edge == BUTTON_PRESSED:
            self.activate()
            self.lightshow_on = False

    def lightshow(self):
        self.lightshow_on = True
        # first, set callback to interrupt the show
        for i in range(self.nbuttons):
            self.trellis.callbacks[i] = self.end_lightshow
        # now pick buttons and flash lights on/off in random order
        while True:
            button_indices = list(range(self.nbuttons))
            random.shuffle(button_indices)
            for i in button_indices:
                self.trellis.pixels[i] = random_color()
                time.sleep(.07)
                if not self.lightshow_on:
                    return
            for i in button_indices:
                self.trellis.pixels[i] = self.colors['off']
                time.sleep(.07)
                if not self.lightshow_on:
                    return
            self.sync()
            time.sleep(.02)

    def set_color_all_buttons(self, color):
        for i in range(self.nbuttons):
            self.set_color(i, color)

    def set_color(self, index, color):
        if color in self.color_map:
            color = self.color_map[color]
        self.trellis.pixels[index] = self.colors[color]

    def sync(self):
        self.trellis.sync()

    def terminate(self):
        for i in range(self.nbuttons):
            self.trellis.pixels[i] = self.colors['off']
        self.sync()
