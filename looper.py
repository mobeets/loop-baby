"""
/usr/bin/jackd -T -ndefault -R -d alsa &
sooperlooper -q -U osc.udp://localhost:11016/ -p 9951 -l 1 -c 2 -t 40 -m ~/loop-baby/midi_bindings.slb
"""
import sys
import time
import argparse
try:
    from trellis import Trellis
except:
    print('WARNING: Could not import Trellis')
from keyboard import Keyboard
from osc_interface import OscSooperLooper

BUTTON_PRESSED = 3
BUTTON_RELEASED = 2

# {button_name: button_index_to_trellis, ...}
BUTTON_NAME_INVERSE = {
     1:  12,  2:   8,  3:  4,  4:  0,
     5:  13,  6:   9,  7:  5,  8:  1,
    'A': 14, 'B': 10, 'C': 6, 'D': 2,
    'E': 15, 'F': 11, 'G': 7, 'H': 3
    }
BUTTON_NAME_MAP = dict((BUTTON_NAME_INVERSE[key],key) for key in BUTTON_NAME_INVERSE)

BUTTON_GROUPS = {
    'mode_buttons': ['A', 'B', 'C', 'D', 'F', 'G'],
    'track_buttons': range(1,8),
    'play_pause': ['E'],
    }

BUTTON_ACTION_MAP = {
    'A': 'oneshot',
    'B': 'save/recall',
    'C': 'clear',
    'D': 'settings',
    'E': 'play/pause',
    'F': 'record',
    'G': 'overdub',
    'H': 'mute',
    }

MODE_COLOR_MAP = {
    None: 'gray',
    'oneshot': 'green',
    'save': 'yellow',
    'recall': 'yellow',
    'clear': 'blue',
    'settings': 'gray',
    'play': 'green',
    'pause': 'yellow',
    'record': 'red',
    'overdub': 'orange',
    'mute': 'blue',
    }

class Loop:
    def __init__(self, track, client):
        self.track = track
        self.client = client
        self.is_playing = False
        self.is_muted = False
        self.is_recording = False
        self.is_overdubbing = False
        self.stopped_overdub_id = None
        self.stopped_record_id = None
        self.has_had_something_recorded = False

    def toggle(self, mode, event_id=None):
        if mode == 'record':
            if self.stopped_record_id == event_id and event_id is not None:
                # already handled this event (preemptively)
                return
            self.is_recording = not self.is_recording
            self.client.hit(mode, self.track)
            self.has_had_something_recorded = True

        elif mode == 'overdub':
            if self.stopped_overdub_id == event_id and event_id is not None:
                # already handled this event (preemptively)
                return
            self.is_overdubbing = not self.is_overdubbing
            self.client.hit(mode, self.track)
            self.has_had_something_recorded = True

        elif mode == 'pause':
            if self.is_playing:
                self.client.hit('pause_on', self.track)
            else:
                self.client.hit('pause_off', self.track)
            self.is_playing = not self.is_playing

        elif mode == 'mute':
            if self.is_muted:
                self.client.hit('mute_off', self.track)
            else:
                self.client.hit('mute_on', self.track)
            self.is_muted = not self.is_muted

    def stop_record_or_overdub(self, event_id):
        """
        okay sorry, this is horrible, but every time a button
        is pressed, we will run this, which will check if the
        loop is recording (or overdubbing), and if it is,
        stop it, and mark the event_id that stopped it.

        the situation we need to handle is that the button
        that was pressed was a button explicitly trying to stop
        recording...so in toggle(), we only toggle something if
        the event_id's don't match
        """
        self.stopped_overdub_id = None
        self.stopped_record_id = None
        if self.is_recording:
            self.is_recording = not self.is_recording
            self.client.hit('record', self.track)
            self.stopped_record_id = event_id
        elif self.is_overdubbing:
            self.is_overdubbing = not self.is_overdubbing
            self.client.hit('overdub', self.track)
            self.was_stopped_overdubbing = True
            self.stopped_overdub_id = event_id

class Looper:
    def __init__(self, client, interface, startup_color='blue',
        nloops=1,  verbose=False, button_action_map=BUTTON_ACTION_MAP,
        button_name_map=BUTTON_NAME_MAP, button_groups=BUTTON_GROUPS,
        mode_color_map=MODE_COLOR_MAP):

        self.verbose = verbose
        self.interface = interface
        self.interface.set_callback(self.button_handler)
        self.client = client
        self.client.verbose = self.verbose

        self.button_action_map = button_action_map
        self.nloops = nloops
        self.loops = [Loop(i, client) for i in range(nloops)]

        # define button groups
        self.button_name_map = button_name_map
        self.button_index_map = dict((v,k) for k,v in button_name_map.items())
        self.button_groups = button_groups
        for k,vs in self.button_groups.items():
            vs = [self.button_index_map[n] for n in vs]
            self.interface.define_color_group(k, vs)
        self.mode_color_map = mode_color_map

        # state variables:
        self.current_loop = 1
        self.client.set('selected_loop_num', self.current_loop-1)
        self.is_playing = False
        self.mode = None
        self.modes = [None, 'record', 'overdub', 'mute', 'oneshot',
            'save', 'load', 'clear', 'settings']
        self.event_id = 0

    def add_loop(self):
        self.client.add_loop()
        self.loops.append(Loop(self.nloops, self.client))
        self.nloops = len(self.loops)

    def button_handler(self, event):
        self.event_id += 1
        if event.edge == BUTTON_PRESSED:
            event_type = 'pressed'
        elif event.edge == BUTTON_RELEASED:
            event_type = 'released'
        else:
            event_type = None

        button_number = event.number
        button_name = self.button_name_map[button_number]
        action = self.button_action_map.get(button_name, button_name)
        if self.verbose:
            print('Button {}: ({}, {}, {})'.format(event_type, action, button_number, button_name))
        self.process_button(button_number, action, event_type, self.event_id)

    def process_button(self, button_number, action, press_type, event_id):
        # updates happen at the time of button press
        if press_type == 'pressed':
            # any time a button is pressed, we must
            # stop any recording/overdubbing going on
            for loop in self.loops:
                loop.stop_record_or_overdub(event_id)

            # now handle
            if type(action) is int:
                self.process_track_change(action, button_number, event_id)
            else:
                self.process_mode_change(action, button_number, event_id)

        # below we just manage colors upon button release
        elif press_type == 'released':
            if type(action) is int:
                if self.mode in [None, 'oneshot', 'clear']:
                    # button press was a oneshot, so turn off light
                    self.interface.un_color(button_number)
            else:
                if self.mode == 'play/pause' and not self.is_playing:
                    print('Uncoloring for pause')
                    self.interface.un_color('play_pause')

    def process_mode_change(self, mode, button_number, event_id):
        """
        the only mode that does something when pressed is 'play/pause'
        otherwise, we may need to handle button colors, but we otherwise
        just wait until a track button is pressed to do anything
        """
        if self.verbose:
            print('   Mode change: {} -> {}'.format(self.mode, mode))

        if mode == 'play/pause': # applies to all loops
            if self.is_playing:
                # set_sync_pos so that when we un-pause, we ensure all loops are re-synced to the same timing
                self.client.hit('set_sync_pos', -1)
                self.client.hit('pause_on', -1)
                if self.mode in ['record', 'overdub', 'mute']:
                    print('   Cannot {} when paused, so exiting {} mode'.format(self.mode, self.mode))
                    self.interface.un_color('mode_buttons')
                    self.mode = None
            else:
                self.client.hit('trigger', -1)
            self.is_playing = not self.is_playing
            color = self.mode_color_map['play'] if self.is_playing else self.mode_color_map['pause']
            self.interface.set_color(button_number, color)
            return

        if mode in ['record', 'overdub', 'mute'] and not self.is_playing:
            print('   Cannot {} when paused; otherwise loops will get out of sync!'.format(mode))
            return
        
        # changing to any other type of mode clears all buttons (except play/pause)
        self.interface.un_color('mode_buttons')
        self.interface.un_color('track_buttons')
        previous_mode = self.mode

        if mode == 'save/recall': # toggles
            if previous_mode == 'save':
                mode = 'recall'
            else:
                mode = 'save'
        color = self.mode_color_map[mode]
        self.interface.set_color(button_number, color)
        self.mode = mode

        if mode == 'clear':
            print('   Clear mode not implemented yet.')

        elif mode == 'settings':
            print('   Settings mode not implemented yet.')

        elif mode == 'save':
            print('   Save mode not implemented yet.')
        
        elif mode == 'recall':
            print('   Recall mode not implemented yet.')

    def process_track_change(self, track, button_number, event_id):
        """
        actions depend on what mode we're in
        we also set button color based on the mode
        """
        if self.verbose:
            print('   ({}) track = {}'.format(self.mode, track))
        color = self.mode_color_map[self.mode]


        if self.mode == None:
            self.interface.set_color(button_number, color)
            if track > self.nloops:
                print('   Creating new loop: {}'.format(self.nloops+1))
                self.add_loop()

        elif self.mode == 'oneshot':
            if track <= self.nloops:
                # warning: hitting oneshot unpauses the track...
                self.current_loop = track
                self.client.hit(self.mode, self.current_loop-1)
                self.interface.set_color(button_number, color)
            else:
                print('   Creating new loop: {}'.format(self.nloops+1))
                self.add_loop()
                # print('   Loop index does not exist for '.format(self.mode))

        elif self.mode in ['record', 'overdub']:
            if track <= self.nloops:
                self.current_loop = track
                self.loops[self.current_loop-1].toggle(self.mode, event_id)
                self.interface.set_color(button_number, color,
                    uncolor='track_buttons')
            else:
                # todo: create loop (and default to one loop)
                print('   Loop index does not exist for '.format(self.mode))

        elif self.mode == 'mute':
            if track <= self.nloops:
                self.current_loop = track
                self.loops[self.current_loop-1].toggle(self.mode)
                self.interface.set_color(button_number, color)
            else:
                print('   Loop index does not exist for '.format(self.mode))

        elif self.mode == 'save':
            print('   Save not implemented yet.')
            self.interface.set_color(track, color)

        elif self.mode == 'load':
            # if we press a track that isn't an option, do nothing
            print('   Load track not implemented yet.')
            self.interface.un_color(button_number)

        elif self.mode == 'clear':
            # if we press a track that isn't an option, do nothing
            print('   Clear track not implemented yet.')
            self.interface.un_color(button_number)

        elif self.mode == 'settings':
            print('   Settings track not implemented yet.')
            self.interface.un_color(button_number)

    def start(self):
        """
        if this doesn't work, is multithreading what we want?
            1. trellis: syncs, pauses every 0.02, triggers callbacks
            2. looper: processes any callbacks triggered by trellis
        """
        if self.verbose:
            print('Looper on!')
        try:
            while True:
                self.interface.sync()
                time.sleep(.02)
        except KeyboardInterrupt:
            # Properly close the system.
            if self.verbose:
                print()
                print('Ending looper...')
            self.client.terminate()
            self.interface.terminate()
            if self.verbose:
                print('See ya!')

def main(args):
    # connect to SooperLooper via OSC
    if args.verbose:
        print('Setting up Sooper Looper OSC client...')
    client = OscSooperLooper(client_url=args.osc_url)

    # connect with either trellis PCB or keyboard
    if args.verbose:
        print('Initializing {} interface...'.format(args.interface))
    if args.interface == 'trellis':
        interface = Trellis(startup_color=args.color)
    elif args.interface == 'keyboard':
        interface = Keyboard(BUTTON_PRESSED, BUTTON_RELEASED)

    looper = Looper(client=client,
        interface=interface,
        verbose=args.verbose)
    looper.start()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="looper")
    parser.add_argument('-v', '--verbose',
        dest='verbose', action='store_true',
        default=True)
    parser.add_argument('-i', '--interface',
        choices=['keyboard', 'trellis'],
        default='trellis')
    parser.add_argument('-c', '--color', type=str,
        choices=['purple', 'red', 'gray', 'green',
        'blue', 'orange'], default='blue')
    parser.add_argument('-o', '--osc_url', type=str,
        default='thisbemymachine.verizon.net')
    args = parser.parse_args()
    main(args)
