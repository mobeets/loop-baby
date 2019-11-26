import time
from board import SCL, SDA
import busio
from adafruit_neotrellis.neotrellis import NeoTrellis
from looper import BUTTON_NAME_INVERSE, BUTTON_NAME_MAP

BUTTON_PRESSED = NeoTrellis.EDGE_RISING
BUTTON_RELEASED = NeoTrellis.EDGE_FALLING

COMMANDS = {'shutdown': [1,4,'E','H'], # shutdown the pi,
    'hard_restart': ['A','B','C','D'], # restart the pi,
    'soft_restart': ['E','F','G','H'], # kills everything, then restarts it all
}
CALLBACKS = {'shutdown': lambda: print('Shutting down.'),
    'hard_restart': lambda: print('Hard restart.'),
    'soft_restart': lambda: print('Soft restart.'),
}

class MultiPress:
    def __init__(self, commands=None, callbacks=None):
        self.commands = commands
        self.callbacks = callbacks
        self.buttons_pressed = set()

    def check_for_matches(self):
        for command, password in self.commands.items():
            if self.buttons_pressed.issuperset(password):
                # call the callback for this command
                self.callbacks[command]()
                # remove those keys from our buttons_pressed queue
                # so we can't execute this multiple times
                self.buttons_pressed.difference_update(password)

    def button_handler(self, event):
        button_number = event.number
        button_name = BUTTON_NAME_MAP[button_number]

        if event.edge == BUTTON_PRESSED:
            self.buttons_pressed.add(button_name)
        elif event.edge == BUTTON_RELEASED:
            if button_name in self.buttons_pressed:
                self.buttons_pressed.remove(button_name)
        self.check_for_matches()

def main():
    # create the i2c object for the trellis
    i2c_bus = busio.I2C(SCL, SDA)

    # create the trellis
    trellis = NeoTrellis(i2c_bus)

    handler = MultiPress(commands=COMMANDS,
        callbacks=CALLBACKS)

    # add button handler
    for i in range(16):
        # activate rising edge events on all keys
        trellis.activate_key(i, BUTTON_PRESSED)
        # activate falling edge events on all keys
        trellis.activate_key(i, BUTTON_RELEASED)
        # set all keys to trigger the blink callback
        trellis.callbacks[i] = handler.button_handler

    # wait for keys to be pressed
    while True:
        trellis.sync()
        time.sleep(.02)

if __name__ == '__main__':
    main()
