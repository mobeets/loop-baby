"""
[start jackd]
$ qjackctl &
$ a2jmidid -e &
$ sooperlooper % # or start gui...
$ python3 looper_trellis.py
"""
import sys
import time
import queue
import struct
import jack

from connect_to_jack import make_ports_and_connections
from mymidi import MidiOutWrapper

from trellis import activate_trellis, trellis, NeoTrellis, PURPLE, OFF

client = jack.Client('looper-trellis')
midi_out = client.midi_outports.register('output')
midi_msgs = queue.Queue()

# this will be called when button events are received
def blink(event):
    # turn the LED on when a rising edge is detected
    if event.edge == NeoTrellis.EDGE_RISING:
        trellis.pixels[event.number] = PURPLE
        print(event.number)
        if event.number % 2 == 0:
            # undo: ch1 program change 0
            print('Undo')
            midi_msgs.put(MidiOutWrapper.program_change(0))
        else:
            # record: ch1 program change 5
            print('Record')
            midi_msgs.put(MidiOutWrapper.program_change(5))

    # # turn the LED off when a rising edge is detected
    elif event.edge == NeoTrellis.EDGE_FALLING:
        trellis.pixels[event.number] = OFF

@client.set_process_callback
def process(frames):
    global midi_msgs
    global trellis
    midi_out.clear_buffer()
    try:
        while True:
            trellis.sync()
            offset = 0
            midi_msg = midi_msgs.get(block=False)            
            midi_out.write_midi_event(offset, midi_msg)
    except queue.Empty:
        pass

try:
    with client:
        success = make_ports_and_connections(client, midi_out)
        if not success:
            sys.exit()
        activate_trellis(blink, PURPLE)

        print('#' * 80)
        print('press Return to quit')
        print('#' * 80)
        # trellis.sync()
        time.sleep(.02)
        input()
except KeyboardInterrupt:
    # handle quitting with ctrl+c
    pass
