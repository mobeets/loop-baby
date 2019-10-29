import jack
import struct
import time
import queue

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

NOTEON = 0x90
NOTEOFF = 0x80

client = jack.Client('MIDI-Chord-Generator')
midi_out = client.midi_outports.register('output')
midi_msgs = queue.Queue()

connect_to = 'qsynth:midi'
fs = None
offset = 0
count = 0
pitch = 80

@client.set_samplerate_callback
def samplerate(samplerate):
    global fs
    fs = samplerate


#this will be called when button events are received
def blink(event):
    #turn the LED on when a rising edge is detected
    if event.edge == NeoTrellis.EDGE_RISING:
        trellis.pixels[event.number] = PURPLE
        print(event.number)
        midi_msgs.put((NOTEON, event.number))

    #turn the LED off when a rising edge is detected
    elif event.edge == NeoTrellis.EDGE_FALLING:
        trellis.pixels[event.number] = OFF
        midi_msgs.put((NOTEOFF, event.number))

@client.set_process_callback
def process(frames):
    global midi_msgs
    global trellis
    midi_out.clear_buffer()
    try:
        while True:
            trellis.sync()
            midi_msg = midi_msgs.get(block=False)
            pitch = 60 + midi_msg[1]
            vel = 100

            msg = struct.pack('3B', midi_msg[0], pitch, vel)
            print('on' if midi_msg[0] == NOTEON else 'off', midi_msg[1], pitch)
            midi_out.write_midi_event(offset, msg)
    except queue.Empty:
        pass

"""
TODO:
- source: https://github.com/spatialaudio/jackclient-python/issues/47
Please note, however, that writing each MIDI event with offset 0 might introduce audible jitter, especially with very long JACK block sizes. In such a situation, I would probably try to obtain client.frame_time in each of the functions, adding a fixed delay (to stay causal) and transmitting this time to the process callback together with the MIDI data. The process callback can then use client.last_frame_time to calculate an appropriate offset value for write_midi_event().
"""

print(client.get_ports())
print('Sample rate: {}'.format(fs))

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
    with client:
        if connect_to:
            client.connect(midi_out, connect_to)
        print('#' * 80)
        print('press Return to quit')
        print('#' * 80)
        # trellis.sync()
        time.sleep(.02)
        input()
except KeyboardInterrupt:
    # handle quitting with ctrl+c
    pass
