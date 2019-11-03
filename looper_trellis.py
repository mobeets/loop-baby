"""
What I did last time:
    $ qjackctl &
        # this implicitly started the following jackd process
        # /usr/bin/jackd -dalsa -dhw:system -r48000 -p1024 -n2
    $ a2jmidid -e &
    # [started sooperlooper gui]
    # [ran this script but without making connections; made them manually after this script started]
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

BUTTON_MAP_INVERSE = {
    '1': 12, '2': 8, '3': 4, '4': 0,
    '5': 13, '6': 9, '7': 5, '8': 1,
    'A': 14, 'B': 10, 'C': 6, 'D': 2,
    'E': 15, 'F': 11, 'G': 7, 'H': 3
    }
BUTTON_MAP = dict((BUTTON_MAP_INVERSE[key],key) for key in BUTTON_MAP_INVERSE)

# specified in midi_bindings.slb
MIDI_ACTION = {
    'Undo': 0,
    'Redo': 1,
    'Record': 5,
    'Overdub': 6,
    'Mute': 9,
    'Pause': 10}

BUTTON_ACTION = {
    'A': 'Undo',
    'B': 'Mute',
    'E': 'Pause',
    'F': 'Record',
    'G': 'Overdub',
    }

# this will be called when button events are received
def blink(event):
    # turn the LED on when a rising edge is detected
    if event.edge == NeoTrellis.EDGE_RISING:
        trellis.pixels[event.number] = PURPLE
        print(event.number)
        if event.number in BUTTON_ACTION:
            action = BUTTON_ACTION[BUTTON_MAP[event.number]]
            print(action)
            midi_msg = MIDI_ACTION[action]
            midi_msgs.put(MidiOutWrapper.program_change(midi_msg))
        else:
            print('No action for {}'.format(event.number))

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
