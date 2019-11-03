# -*- coding: utf-8 -*-
import struct

###################################################
# Midi channel events (the most common events)
# Also called "Channel Voice Messages"

NOTE_OFF = 0x80
# 1000cccc 0nnnnnnn 0vvvvvvv (channel, note, velocity)

NOTE_ON = 0x90
# 1001cccc 0nnnnnnn 0vvvvvvv (channel, note, velocity)

POLYPHONIC_PRESSURE = POLY_PRESSURE = 0xA0
# 1010cccc 0nnnnnnn 0vvvvvvv (channel, note, velocity)

# see Channel Mode Messages for Controller Numbers
CONTROLLER_CHANGE = CONTROL_CHANGE = 0xB0
# 1011cccc 0ccccccc 0vvvvvvv (channel, controller, value)

PROGRAM_CHANGE = 0xC0
# 1100cccc 0ppppppp (channel, program)

CHANNEL_PRESSURE = MONO_PRESSURE = 0xD0
# 1101cccc 0ppppppp (channel, pressure)

PITCH_BEND = 0xE0
# 1110cccc 0vvvvvvv 0wwwwwww (channel, value-lo, value-hi)

class MidiOutWrapper:
    @staticmethod
    def channel_message(command, *data, ch=1):
        """Send a MIDI channel mode message."""
        command = (command & 0xf0) | (ch - 1 & 0xf)
        msg = [command] + [value & 0x7f for value in data]
        return struct.pack(str(len(data)+1) + 'B', *msg)

    @staticmethod
    def note_off(note, velocity=0, ch=1):
        """Send a 'Note Off' message."""
        return MidiOutWrapper.channel_message(NOTE_OFF, note, velocity, ch=ch)

    @staticmethod
    def note_on(note, velocity=127, ch=1):
        """Send a 'Note On' message."""
        return MidiOutWrapper.channel_message(NOTE_ON, note, velocity, ch=ch)

    @staticmethod
    def program_change(program, ch=1):
        """Send a 'Program Change' message."""
        return MidiOutWrapper.channel_message(PROGRAM_CHANGE, program, ch=ch)
