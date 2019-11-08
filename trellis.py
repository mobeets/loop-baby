import time
from board import SCL, SDA
import busio
from adafruit_neotrellis.neotrellis import NeoTrellis

class Trellis:
    """
    relays button presses by adding them to a queue
    buttons can be referred to by name, index, or color group name
    """
    def __init__(self, q, color=None, button_names=BUTTON_NAMES, debug=True):

        self.debug = debug
        self.nbuttons = 16
        self.colors = {'off': (0, 0, 0), 'purple': (180, 0, 255),
            'red': (255, 0, 0), 'orange': (255, 160, 0),
            'gray': (100, 100, 100), 'blue': (0, 0, 255)}
        
        # for converting event.index into button name
        self.button_names = button_names
        self.button_indices = dict((v,k) for k,v in self.button_names)

        # create the i2c object for the trellis
        self.i2c_bus = busio.I2C(SCL, SDA)

        # create the trellis
        self.trellis = NeoTrellis(i2c_bus) # can set interrupt=True here...

        # queue to store button presses
        self.q = q

        # for handling colors of groups of buttons
        self.color_groups = {}

        # set handlers for button press
        self.activate(color)

    def activate(self, color=None):
        for i in range(self.nbuttons):
            #activate rising edge events on all keys
            trellis.activate_key(i, NeoTrellis.EDGE_RISING)
            #activate falling edge events on all keys
            trellis.activate_key(i, NeoTrellis.EDGE_FALLING)
            #set all keys to trigger the blink callback
            trellis.callbacks[i] = self.handle_button_press

            #cycle the LEDs on startup
            if color is not None:
                trellis.pixels[i] = color
                time.sleep(.05)

        for i in range(self.nbuttons):
            trellis.pixels[i] = self.colors['off']
            time.sleep(.05)

    def handle_button_press(self, event):        
        if event.edge == NeoTrellis.EDGE_RISING:
            event_type = 'pressed'
        elif event.edge == NeoTrellis.EDGE_FALLING:
            event_type = 'released'
        else:
            event_type = None
        self.q.put_nowait((event.number, event_type))
        if self.debug:
            print("Button event: {}, {}".format(event.number, event_type))

    def define_color_group(self, group_name, button_numbers):
        self.color_groups[group_name] = button_numbers

    def set_color_of_group(group_name, color):
        for i in self.color_groups[group_name]:
            trellis.pixels[i] = self.colors[color]

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
            self.set_color_of_group(group_name, 'off')
