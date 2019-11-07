import time
from board import SCL, SDA
import busio
from adafruit_neotrellis.neotrellis import NeoTrellis

#create the i2c object for the trellis
i2c_bus = busio.I2C(SCL, SDA)
print (i2c_bus)

#create the trellis
trellis = NeoTrellis(i2c_bus) # can set interrupt=True here...
print(trellis)

#some color definitions
OFF = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 150, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)

def activate_trellis(callback, color):
    for i in range(16):
        #activate rising edge events on all keys
        trellis.activate_key(i, NeoTrellis.EDGE_RISING)
        #activate falling edge events on all keys
        trellis.activate_key(i, NeoTrellis.EDGE_FALLING)
        #set all keys to trigger the blink callback
        trellis.callbacks[i] = callback

        #cycle the LEDs on startup
        trellis.pixels[i] = color
        time.sleep(.05)

    for i in range(16):
        trellis.pixels[i] = OFF
        time.sleep(.05)
