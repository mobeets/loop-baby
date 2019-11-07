import time
from board import SCL, SDA
import busio
from adafruit_neotrellis.neotrellis import NeoTrellis

# {button_name: button_index_to_trellis, ...}
BUTTON_NAME_INVERSE = {
     1:  12,  2:   8,  3:  4,  4:  0,
     5:  13,  6:   9,  7:  5,  8:  1,
    'A': 14, 'B': 10, 'C': 6, 'D': 2,
    'E': 15, 'F': 11, 'G': 7, 'H': 3
    }
BUTTON_NAME = dict((BUTTON_NAME_INVERSE[key],key) for key in BUTTON_NAME_INVERSE)

class Trellis:
    """
    relays button presses by adding them to a queue
    """
    def __init__(self, q, color=None, BUTTON_NAME=BUTTON_NAME, debug=True):

        self.debug = debug
        self.nbuttons = 16
        self.colors = {'off': (0, 0, 0), 'purple': (180, 0, 255),
            'red': (255, 0, 0), 'gray': (100, 100, 100),
            'blue': (0, 0, 255)}
        
        # for converting event.index into button name
        self.button_name = BUTTON_NAME

        # create the i2c object for the trellis
        self.i2c_bus = busio.I2C(SCL, SDA)

        # create the trellis
        self.trellis = NeoTrellis(i2c_bus) # can set interrupt=True here...

        # queue to store button presses
        self.q = q

        # set handlers for button press
        self.activate(color)

    def activate(self, color=None):
        for i in range(NBUTTONS):
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

        for i in range(NBUTTONS):
            trellis.pixels[i] = OFF
            time.sleep(.05)

    def handle_button_press(self, event):        
        button = self.button_name[event.number]
        if event.edge == NeoTrellis.EDGE_RISING:
            event_type = 'pressed'
        elif event.edge == NeoTrellis.EDGE_FALLING:
            event_type = 'released'
        else:
            event_type = None
        self.q.put_nowait((button, event_type))
        if self.debug:
            print("Button event: {}, {}".format(button, event_type))

    def set_color(self, index, color):
        self.trellis.pixels[index] = self.colors[color]

    def no_color(self, index):
        self.trellis.pixels[index] = self.colors['off']
