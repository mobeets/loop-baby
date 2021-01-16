import sys
import time
import glob
import pygame
import os.path

from board import SCL, SDA
import busio
from adafruit_neotrellis.neotrellis import NeoTrellis

# init audio
# source: https://stackoverflow.com/questions/18273722/pygame-sound-delay
# init(frequency, size, channels, buffer)
pygame.mixer.pre_init(22050, -16, 2, 512)
pygame.init()
pygame.mixer.quit()
pygame.mixer.init(22050, -16, 2, 512)
print('Initiated pygame')

# load samples
sample_dir = 'static/samples'
try:
    sample_name = sys.argv[1]
except:
    sample_name = 'wurly'

soundfiles = glob.glob(os.path.join(sample_dir, sample_name, '*.wav'))
samples = [pygame.mixer.Sound(soundfile) for soundfile in soundfiles]
print('Loaded {} samples from {}'.format(len(samples), sample_name))

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

#this will be called when button events are received
def blink(event):
    #turn the LED on when a rising edge is detected
    if event.edge == NeoTrellis.EDGE_RISING:
        trellis.pixels[event.number] = CYAN
        print(event.number)
        samples[event.number % len(samples)].play()

    #turn the LED off when a rising edge is detected
    elif event.edge == NeoTrellis.EDGE_FALLING:
        trellis.pixels[event.number] = OFF

for i in range(16):
    #activate rising edge events on all keys
    trellis.activate_key(i, NeoTrellis.EDGE_RISING)
    #activate falling edge events on all keys
    trellis.activate_key(i, NeoTrellis.EDGE_FALLING)
    #set all keys to trigger the blink callback
    trellis.callbacks[i] = blink

    #cycle the LEDs on startup
    trellis.pixels[i] = PURPLE
    time.sleep(.05)

for i in range(16):
    trellis.pixels[i] = OFF
    time.sleep(.05)

try:
    while True:
        #call the sync function call any triggered callbacks
        trellis.sync()
        #the trellis can only be read every 17 millisecons or so
        time.sleep(.02)
except KeyboardInterrupt:
    # handle quitting with ctrl+c
    pass
