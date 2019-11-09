import sys
import time
from trellis import Trellis, BUTTON_PRESSED, BUTTON_RELEASED
from osc_interface import OscSooperLooperInterface

# {button_name: button_index_to_trellis, ...}
BUTTON_NAME_INVERSE = {
     1:  12,  2:   8,  3:  4,  4:  0,
     5:  13,  6:   9,  7:  5,  8:  1,
    'A': 14, 'B': 10, 'C': 6, 'D': 2,
    'E': 15, 'F': 11, 'G': 7, 'H': 3
    }
BUTTON_NAME_MAP = dict((BUTTON_NAME_INVERSE[key],key) for key in BUTTON_NAME_INVERSE)

BUTTON_GROUPS = {
    'mode_buttons': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
    'track_buttons': range(1,8),
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
    def __init__(self, track, interface):
        self.track = track
        self.interface = interface
        self.is_playing = False
        self.is_recording = False
        self.is_overdubbing = False
        self.stopped_overdub_id = None
        self.stopped_record_id = None

    def toggle(self, mode, event_id=None):
        if mode == 'record':
            if self.stopped_record_id == event_id and event_id is not None:
                # already handled this event (preemptively)
                return
            self.is_recording = not self.is_recording
            self.interface.hit(mode, self.track-1)
        elif mode == 'overdub':
            if self.stopped_overdub_id == event_id and event_id is not None:
                # already handled this event (preemptively)
                return
            self.is_overdubbing = not self.is_overdubbing
            self.interface.hit(mode, self.track-1)
        elif mode == 'pause':
            self.is_playing = not self.is_playing
            self.interface.hit(mode, self.track-1)

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
            self.interface.hit('record', self.track-1)
            self.stopped_record_id = event_id
        elif self.is_overdubbing:
            self.is_overdubbing = not self.is_overdubbing
            self.interface.hit('overdub', self.track-1)
            self.was_stopped_overdubbing = True
            self.stopped_overdub_id = event_id

class Looper:
    def __init__(self, interface, startup_color='blue', nloops=2,  verbose=False, button_action_map=BUTTON_ACTION_MAP,
        button_name_map=BUTTON_NAME_MAP, button_groups=BUTTON_GROUPS,
        mode_color_map=MODE_COLOR_MAP):

        self.verbose = verbose
        
        self.trellis = Trellis(self.button_handler, startup_color=startup_color)
        if self.verbose:
            print('Initializing looper...')
            print('Trellis initialized.')
        self.interface = interface

        self.button_action_map = button_action_map
        self.nloops = nloops
        self.loops = [Loop(i, interface) for i in range(nloops)]

        # define button groups
        self.button_name_map = button_name_map
        self.button_index_map = dict((v,k) for k,v in button_name_map.items())
        self.button_groups = button_groups
        for k,vs in self.button_groups.items():
            vs = [self.button_index_map[n] for n in vs]
            self.trellis.define_color_group(k, vs)
        self.mode_color_map = mode_color_map

        # state variables:
        self.current_loop = 1
        self.interface.set('selected_loop_num', self.current_loop-1)
        self.is_playing = False
        self.mode = None
        self.modes = [None, 'record', 'overdub', 'mute', 'oneshot',
            'save', 'load', 'clear', 'settings']
        self.event_id = 0

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
                    self.trellis.un_color(button_number)

    def process_mode_change(self, mode, button_number, event_id):
        """
        the only mode that does something when pressed is 'play/pause'
        otherwise, we may need to handle button colors, but we otherwise
        just wait until a track button is pressed to do anything
        """
        if self.verbose:
            print('   Mode change: {} -> {}'.format(self.mode, mode))

        if mode == 'play/pause': # applies to all loops
            self.is_playing = not self.is_playing
            color = self.mode_color_map['play'] if self.is_playing else self.mode_color_map['pause']
            self.trellis.set_color(button_number, color)
            for loop in self.loops:
                loop.toggle('pause')
            return

        # changing to any other type of mode clears all buttons
        self.trellis.un_color('mode_buttons')
        self.trellis.un_color('track_buttons')
        previous_mode = self.mode
        
        if mode == 'save/recall': # toggles
            if previous_mode == 'save':
                mode = 'recall'
            else:
                mode = 'save'
        color = self.mode_color_map[mode]
        self.trellis.set_color(button_number, color)
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

        # todo: if we are currently recording/overdubbing, we need to STOP recording/overdubbing
        # unless...the button we're about to press is going to explicitly end that, in which case we don't want to do it pre-emptively!
        # basically my best guess is that, if we're recording/overdubbing track 1, unless the button we're hitting is track 1 again, we want to stop recording

        if self.mode == None:
            self.trellis.set_color(button_number, color)

        elif self.mode == 'oneshot':
            # warning: possible that hitting oneshot unpauses the track?
            self.current_loop = track
            self.interface.hit(self.mode, self.current_loop-1)
            self.trellis.set_color(button_number, color)

        elif self.mode in ['record', 'overdub']:
            self.current_loop = track
            self.loops[self.current_loop-1].toggle(self.mode, event_id)
            self.trellis.set_color(button_number, color,
                uncolor='track_buttons')

        elif self.mode == 'save':
            print('   Save not implemented yet.')
            self.trellis.set_color(track, color)

        elif self.mode == 'load':
            # if we press a track that isn't an option, do nothing
            print('   Load track not implemented yet.')
            self.trellis.un_color(button_number)

        elif self.mode == 'clear':
            # if we press a track that isn't an option, do nothing
            print('   Clear track not implemented yet.')
            self.trellis.un_color(button_number)

        elif self.mode == 'settings':
            print('   Settings track not implemented yet.')
            self.trellis.un_color(button_number)

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
                self.trellis.sync()
                time.sleep(.02)
        except KeyboardInterrupt:
            # Properly close the system.
            if self.verbose:
                print()
                print('Ending looper...')
            self.interface.terminate()
            if self.verbose:
                print('See ya!')

def main():    
    interface = OscSooperLooperInterface()
    looper = Looper(interface, verbose=True)
    looper.start()

if __name__ == '__main__':
    main()
