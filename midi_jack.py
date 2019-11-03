import jack
import struct
import time

NOTEON = 0x90
NOTEOFF = 0x80

"""
1. Run qsynth
2. Run this code

Current status: It seems to write the midi events, but no audio is playing. Is qsynth playing audio? Is the midi triggering anything? Maybe the notes are too brief? Who knows.
"""
client = jack.Client('MIDI-Chord-Generator')
midi_out = client.midi_outports.register('output')
connect_to = 'qsynth:midi'
fs = None
offset = 0
count = 0
pitch = 80

@client.set_samplerate_callback
def samplerate(samplerate):
    global fs
    fs = samplerate

max_count = 20*fs

@client.set_process_callback
def process(frames):
    midi_out.clear_buffer()
    global offset
    global count
    global max_count
    global pitch
    while count < max_count:
        vel = 100

        if count % fs == 0:
            msg_on = struct.pack('3B', NOTEON, pitch, vel)
            print(msg_on, 'on', pitch, count)
            midi_out.write_midi_event(offset, msg_on)
        elif count % fs == 20:
            msg_off = struct.pack('3B', NOTEOFF, pitch, vel)
            print(msg_off, 'off', pitch, count)
            midi_out.write_midi_event(offset, msg_off)
        pitch = (pitch + 5) % 120
        count += 1

print(client.get_ports())
print('Sample rate: {}'.format(fs))
client.activate()

with client:
    if connect_to:
        client.connect(midi_out, connect_to)
    print('#' * 80)
    print('press Return to quit')
    print('#' * 80)
    input()

