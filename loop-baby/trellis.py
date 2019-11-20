import time
from board import SCL, SDA
import busio
from adafruit_neotrellis.neotrellis import NeoTrellis

BUTTON_PRESSED = NeoTrellis.EDGE_RISING
BUTTON_RELEASED = NeoTrellis.EDGE_FALLING

class Trellis:
    """
    relays button presses by adding them to a queue
    buttons can be referred to by name, index, or color group name
    """
    def __init__(self, startup_color='red', debug=True):

        self.debug = debug
        self.nbuttons = 16
        self.colors = {'off': (0, 0, 0), 'purple': (180, 0, 255),
            'red': (255, 0, 0), 'orange': (255, 160, 0),
            'green': (0, 255, 0), 'yellow': (255, 255, 0), 
            'gray': (100, 100, 100), 'blue': (0, 0, 255),
            'darkgray': (10, 10, 10),}

        # create the i2c object for the trellis
        self.i2c_bus = busio.I2C(SCL, SDA)

        # create the trellis
        self.trellis = NeoTrellis(self.i2c_bus) # can set interrupt=True here...

        # for handling colors of groups of buttons
        if startup_color not in self.colors:
            print('WARNING: Did not recognize color. Using {}'.format(self.default_color))
            startup_color = self.default_color
        self.startup_color = startup_color
        self.color_groups = {}

        # to ensure callback set
        self.button_handler = None

    def set_callback(self, fcn):
        # callback for when buttons are pressed
        self.button_handler = fcn
        # set handlers for button press
        self.activate(self.startup_color)

    def activate(self, startup_color=None):
        if self.button_handler is None:
            print("Error: callback must be set using 'set_callback'")

        for i in range(self.nbuttons):
            #activate rising edge events on all keys
            self.trellis.activate_key(i, BUTTON_PRESSED)
            #activate falling edge events on all keys
            self.trellis.activate_key(i, BUTTON_RELEASED)
            #set all keys to trigger the blink callback
            self.trellis.callbacks[i] = self.button_handler

            #cycle the LEDs on startup
            if startup_color is not None:
                self.trellis.pixels[i] = self.colors[startup_color]
                time.sleep(.05)

        for i in range(self.nbuttons):
            self.trellis.pixels[i] = self.colors['off']
            time.sleep(.05)

    def define_color_group(self, group_name, button_numbers):
        self.color_groups[group_name] = button_numbers

    def set_color_of_group(self, group_name, color):
        for i in self.color_groups[group_name]:
            self.trellis.pixels[i] = self.colors[color]

    def set_color(self, index, color, uncolor=None):
        if uncolor: # a group name that we want to uncolor
            if uncolor not in self.color_groups:
                print("Error! Undefined color group: {}".format(uncolor))
            else:
                self.un_color(uncolor)
        self.trellis.pixels[index] = self.colors[color]

    def un_color(self, index):
        if type(index) is int:
            self.trellis.pixels[index] = self.colors['off']
        else:
            self.set_color_of_group(index, 'off')

    def sync(self):
        self.trellis.sync()

    def terminate(self):
        for i in range(self.nbuttons):
            self.trellis.pixels[i] = self.colors['off']
