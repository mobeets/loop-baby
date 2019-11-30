import os
import sys
import time
import argparse
try:
    from trellis import Trellis
except:
    print('WARNING: Could not import Trellis')

from loop import Loop
from keyboard import Keyboard
from multipress import MultiPress
from osc import OscSooperLooper
from save_and_recall import SLSessionManager

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

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
    'all': BUTTON_NAME_INVERSE.keys(),
    'mode_buttons': ['A', 'B', 'C', 'D', 'F', 'G', 'H'],
    'track_buttons': [1, 2, 3, 4, 5, 6, 7, 8],
    'play/pause': ['E'],
    }

BUTTON_ACTION_MAP = {
    'A': 'oneshot',
    'B': 'save/recall',
    'C': 'settings',
    'D': 'clear',
    'E': 'play/pause',
    'F': 'record/overdub',
    'G': 'undo/redo',
    'H': 'mute',
    }

MODE_COLOR_MAP = {
    None: 'gray',
    'track': 'gray',
    'play': 'green',
    'pause': 'yellow',
    'record': 'red',
    'overdub': 'orange',
    'mute': 'lightblue',
    'clear': 'blue',
    'undo': 'lightseagreen',
    'redo': 'seagreen',
    'oneshot': 'green',
    'save': 'pink',
    'recall': 'lightorange',
    'settings': 'lightpurple',
    'mute_on': 'lightblue',
    'mute_off': 'gray',
    'track_pressed_once': 'salmon',
    'track_recorded': 'gray',
    'track_exists': 'darkgray',
    'session_exists': 'pink',
    'session_empty': 'darkgray',
    }

META_COMMANDS = {
    'shutdown': { # shutdown the pi,
            'command': [1,2,3,4],
            'restart_looper': False,
            'callback': lambda: os.system('sudo halt')
        },
    'hard_restart': { # restart the pi,
            'command': ['A','B','C','D'],
            'restart_looper': False,
            'callback': lambda: os.system('sudo reboot')
        },
    'soft_restart': { # calls ./startup.sh
            'command': ['E','F','G','H'],
            'restart_looper': True,
            'callback': lambda: os.system('.' + os.path.join(BASE_PATH, 'startup.sh'))
        },
}

class Looper:
    def __init__(self, client, interface, multipress=None,
        sessions=None,
        startup_color='blue', nloops=4, maxloops=8, verbose=False,
        button_action_map=BUTTON_ACTION_MAP,
        button_name_map=BUTTON_NAME_MAP, button_groups=BUTTON_GROUPS,
        mode_color_map=MODE_COLOR_MAP):

        self.verbose = verbose
        self.interface = interface
        self.interface.set_callback(self.button_handler)
        self.client = client
        self.client.verbose = self.verbose
        self.multipress = multipress

        self.button_action_map = button_action_map
        self.action_button_map = dict((v,k) for k,v in button_action_map.items())

        # define button groups
        self.button_name_map = button_name_map
        self.button_index_map = dict((v,k) for k,v in button_name_map.items())
        self.button_groups = button_groups
        for k,vs in self.button_groups.items():
            vs = [self.button_index_map[n] for n in vs]
            self.interface.define_color_group(k, vs)
        self.mode_color_map = mode_color_map
        self.buttons_pressed = set()
        self.tracks_pressed_once = [] # for checking if track double-pressed

        # create loops
        self.nloops = nloops
        self.maxloops = maxloops
        self.sessions = sessions

        # state variables:
        self.client.set('selected_loop_num', 0)
        self.is_playing = True
        self.mode = None
        self.mode_buttons = list(self.action_button_map)
        self.event_id = 0

    def init_loops(self):
        """
        create loops internally, and with SL
        """
        self.loops = [Loop(i, self.client, self.button_index_map[i+1]) for i in range(self.nloops)]
        # one loop exists; must tell SL about the remaining ones
        for i in range(self.nloops-1):
            self.client.add_loop()

    def add_loop(self, internal_add_only=True):
        """
        add an additional loop internally, and with SL
        """
        self.client.add_loop()
        self.loops.append(Loop(self.nloops, self.client, self.button_index_map[self.nloops+1]))
        self.nloops = len(self.loops)

    def check_for_multipress_matches(self):
        """
        check if any buttons currently being pressed are a command
        """
        if self.multipress is None:
            return
        self.buttons_pressed = self.multipress.check_for_matches(self.buttons_pressed, self)

    def button_handler(self, event):
        """
        this gets called when a Trellis button is pressed
        """
        self.event_id += 1
        button_number = event.number
        button_name = self.button_name_map[button_number]
        action = self.button_action_map.get(button_name, button_name)

        if event.edge == BUTTON_PRESSED:
            event_type = 'pressed'
            self.buttons_pressed.add(button_name)
        elif event.edge == BUTTON_RELEASED:
            event_type = 'released'
            if button_name in self.buttons_pressed:
                self.buttons_pressed.remove(button_name)
            else:
                # false event (happens sometimes for some reason)
                return
        else:
            event_type = None
        if self.verbose:
            print('Button {}: ({}, {}, {})'.format(event_type, action, button_number, button_name))
        self.check_for_multipress_matches()
        self.process_button(button_number, action, event_type, self.event_id)

    def process_button(self, button_number, action, press_type, event_id):
        """
        handle a button press based on whether it's mode/track
        and press/release
        then update colors of all buttons
        """
        # updates happen at the time of button press
        if press_type == 'pressed':
            # any time a button is pressed, we will
            # stop any recording/overdubbing going on
            for loop in self.loops:
                loop.stop_record_or_overdub(event_id)

            # now handle the button press
            if type(action) is int:
                self.process_track_change(action, button_number, event_id)
            else:
                self.process_mode_change(action, button_number, event_id)
                self.set_mode_colors_given_mode()
            self.set_track_colors_given_mode()

        # mark when a track button is unpressed
        elif press_type == 'released':
            if type(action) is int and action < len(self.loops):
                self.loops[action-1].is_pressed = False
                self.set_track_colors_given_mode()

    def set_mode_colors_given_mode(self):
        """
        set colors of all mode buttons based on self.mode
        """
        for mode_button in self.mode_buttons:
            button_number = self.button_index_map[self.action_button_map[mode_button]]
            if mode_button == 'play/pause':
                if self.is_playing:
                    color = self.mode_color_map['play']
                else:
                    color = self.mode_color_map['pause']
            elif mode_button == self.mode:
                color = self.mode_color_map[mode_button]
            else:
                color = 'off'
            self.interface.set_color(button_number, color)

    def set_track_colors_given_mode(self):
        """
        set colors of all track buttons based on self.mode
        """
        if self.mode == None:
            for loop in self.loops:
                color = 'off'
                if loop.is_pressed:
                    color = self.mode_color_map['track']
                self.interface.set_color(loop.button_number, color)
        elif self.mode == 'oneshot':
            for loop in self.loops:
                if loop.is_pressed:
                    color = self.mode_color_map[self.mode]
                elif loop.has_had_something_recorded:
                    color = self.mode_color_map['track_recorded']
                else:
                    color = self.mode_color_map['track_exists']
                self.interface.set_color(loop.button_number, color)
        elif self.mode in ['record', 'overdub']:
            # color buttons if track exists but isn't currently being recorded to
            for loop in self.loops:
                if loop.is_recording or loop.is_overdubbing:
                    color = self.mode_color_map[self.mode]
                elif loop.has_had_something_recorded:
                    color = self.mode_color_map['track_recorded']
                else:
                    color = self.mode_color_map['track_exists']
                self.interface.set_color(loop.button_number, color)
        elif self.mode == 'mute':
            for loop in self.loops:
                if not loop.has_had_something_recorded:
                    color = self.mode_color_map['track_exists']
                elif loop.is_muted:
                    color = self.mode_color_map['mute_on']
                else:
                    color = self.mode_color_map['mute_off']
                self.interface.set_color(loop.button_number, color)
        elif self.mode in ['undo', 'redo']:
            for loop in self.loops:
                color = 'off'
                if loop.is_pressed:
                    color = self.mode_color_map[self.mode]
                elif loop.has_had_something_recorded:
                    color = self.mode_color_map['track_exists']
                self.interface.set_color(loop.button_number, color)
        elif self.mode == 'clear':
            for loop in self.loops:
                color = 'off'
                if loop.track+1 in self.tracks_pressed_once:
                    if self.verbose:
                        print('    Refreshing {} {}'.format(loop.button_number, self.tracks_pressed_once))
                    color = self.mode_color_map['track_pressed_once']
                elif loop.has_had_something_recorded:
                    color = self.mode_color_map['track_exists']
                self.interface.set_color(loop.button_number, color)
        elif self.mode in ['save', 'recall']:
            for i in range(self.maxloops):
                if self.sessions.session_exists(i):
                    if i+1 in self.tracks_pressed_once:
                        color = self.mode_color_map['track_pressed_once']
                    else:
                        color = self.mode_color_map['session_exists']
                else:
                    color = self.mode_color_map['session_empty']
                button_number = self.button_index_map[i+1]
                self.interface.set_color(button_number, color)

    def pause(self):
        """
        pause all loops, and mark sync position for when we play
        """
        self.client.hit('set_sync_pos', -1)
        self.client.hit('pause_on', -1)
        if self.mode in ['record', 'overdub', 'mute']:
            print('   Cannot {} when paused, so exiting {} mode'.format(self.mode, self.mode))
            self.mode = None
        self.is_playing = False

    def play(self):
        """
        play all loops
        then re-mute any as necessary, since 'trigger' unmutes all
        """
        if self.mode in ['save', 'recall', 'settings']:
            print('   Cannot {} when playing, so exiting {} mode'.format(self.mode, self.mode))
            self.mode = None
        # when unpausing, 'trigger' restarts from where we paused
        self.client.hit('trigger', -1)
        # but we must now check which tracks were muted and re-mute
        for loop in self.loops:
            loop.remute_if_necessary()
        self.is_playing = True

    def process_mode_change(self, mode, button_number, event_id):
        """
        the only mode that does something when pressed is 'play/pause'
        otherwise, we basically wait until a track button is pressed to do anything
        """
        if self.verbose:
            print('   Mode change: {} -> {}'.format(self.mode, mode))

        if mode == 'play/pause':
            if self.is_playing:
                self.pause()
            else:
                self.play()
            return

        # if we are already in this mode, exit this mode
        if mode == self.mode:
            if self.verbose:
                print('   Already in this mode, so setting mode to None.')
            self.mode = None
            return

        # toggle different modes
        previous_mode = self.mode
        self.mode = mode
        if mode == 'record/overdub':
            mode = 'overdub' if previous_mode == 'record' else 'record'
        elif mode == 'save/recall':
            mode = 'recall' if previous_mode == 'save' else 'save'
        elif mode == 'undo/redo':
            mode = 'redo' if previous_mode == 'undo' else 'undo'

        # handle illegal actions
        if mode in ['record', 'overdub', 'mute'] and not self.is_playing:
            print('   Cannot {} when paused; otherwise loops will get out of sync!'.format(mode))
            return
        if mode in ['save', 'recall', 'settings'] and self.is_playing:
            print('   Cannot {} when playing!'.format(mode))
            return

        if mode == 'clear':
            self.tracks_pressed_once = []
        elif mode in ['save', 'recall']:
            self.tracks_pressed_once = []
            self.sessions.sync()
        elif mode == 'settings':
            print('   Settings mode not implemented yet.')

    def process_track_change(self, track, button_number, event_id):
        """
        actions depend on what mode we're in
        we also set button color based on the mode
        """
        if self.verbose:
            print('   ({}) track = {}'.format(self.mode, track))
        if track < len(self.loops):
            self.loops[track-1].is_pressed = True

        if self.mode == None:
            if track > self.nloops:
                print('   Creating new loop: {}'.format(self.nloops+1))
                self.add_loop()

        elif self.mode == 'oneshot':
            # warning: once you hit this once, this loop will forever
            # be out of sync; this is because we cannot store the sync_pos
            # and then restore it later
            if track <= self.nloops:
                # reset_sync_pos so that it always plays from the top
                self.client.hit('reset_sync_pos', track-1)
                self.client.hit(self.mode, track-1)
                # if will auto-mute when done, so let's just mark this
                # because we just have to deal with what SL wants
                self.loops[track-1].mark_as_muted()
            else:
                print('   Creating new loop: {}'.format(self.nloops+1))
                self.add_loop()

        elif self.mode in ['record', 'overdub']:
            if track <= self.nloops:
                self.loops[track-1].toggle(self.mode, event_id)
            else:
                print('   Loop index does not exist for '.format(self.mode))

        elif self.mode == 'mute':
            if track <= self.nloops:
                self.loops[track-1].toggle(self.mode)
            else:
                print('   Loop index does not exist for {}'.format(self.mode))

        elif self.mode == 'undo':
            if track <= self.nloops:
                self.loops[track-1].undo()
            else:
                print('   Loop index does not exist for {}'.format(self.mode))

        elif self.mode == 'redo':
            if track <= self.nloops:
                self.loops[track-1].redo()
            else:
                print('   Loop index does not exist for {}'.format(self.mode))

        elif self.mode == 'clear':
            if track <= self.nloops:
                if track in self.tracks_pressed_once:
                    if self.verbose:
                        print('   Clearing track {}'.format(track))
                    self.tracks_pressed_once = []
                    self.loops[track-1].clear()
                else:
                    if self.verbose:
                        print('   Pressed track {} once for {}'.format(track, self.mode))
                    self.tracks_pressed_once = [track]
            else:
                print('   Loop index does not exist for {}'.format(self.mode))

        elif self.mode == 'save':
            if not self.sessions.session_exists(track-1) or track in self.tracks_pressed_once:
                self.sessions.save_session(track-1, self.loops)
                self.tracks_pressed_once = []
                if self.verbose:
                    print('   Saving session at index {}'.format(track-1))
            else:
                if self.verbose:
                    print('   Pressed track {} once for {}'.format(track, self.mode))
                self.tracks_pressed_once = [track]

        elif self.mode == 'recall':
            if self.sessions.session_exists(track-1) and track in self.tracks_pressed_once:
                has_audio = self.sessions.load_session(track-1)
                nloops = len(has_audio)
                # remove extra loops (internally)
                if nloops < self.nloops:
                    self.loops = self.loops[:nloops]
                    self.nloops = len(self.loops)
                # add extra loops (internally)
                while nloops > self.nloops:
                    self.add_loop(internal_add_only=True)
                # mark any existing loops that have something recorded
                for i,loop in enumerate(self.loops):
                    loop.has_had_something_recorded = has_audio[i]
                self.tracks_pressed_once = []
                if self.verbose:
                    print('   Loading session at index {}'.format(track-1))
            elif track not in self.tracks_pressed_once:
                if self.verbose:
                    print('   Pressed track {} once for {}'.format(track, self.mode))
                self.tracks_pressed_once = [track]
            else:
                print('   Saved session does not exist at track {}'.format(track))

        elif self.mode == 'settings':
            print('   Settings track not implemented yet.')

    def init_looper(self):
        # load empty session
        self.client.load_empty_session()   
        time.sleep(0.2)
        self.init_loops()
        self.mode = None
        self.is_playing = True
        self.set_mode_colors_given_mode()
        if self.verbose:
            print('Looper on!')
        
    def start(self):
        self.init_looper()
        try:
            while True:
                self.interface.sync()
                time.sleep(.02)
        except KeyboardInterrupt:
            # Properly close the system.
            self.terminate()

    def terminate(self):
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
    client = OscSooperLooper(client_url=args.osc_url,
        empty_session=args.empty_session_file)

    # connect with either trellis PCB or keyboard
    if args.verbose:
        print('Initializing {} interface...'.format(args.interface))
    if args.interface == 'trellis':
        interface = Trellis(startup_color=args.color)
    elif args.interface == 'keyboard':
        interface = Keyboard(BUTTON_PRESSED, BUTTON_RELEASED)
    multipress = MultiPress(META_COMMANDS)
    sessions = SLSessionManager(args.session_dir, client)

    looper = Looper(client=client,
        interface=interface,
        multipress=multipress,
        sessions=sessions,
        verbose=args.verbose)
    try:
        looper.start()
    except:
        looper.terminate()
        raise

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
        'blue', 'orange', 'random'], default='random')
    parser.add_argument('-o', '--osc_url', type=str,
        default='127.0.0.1')
    parser.add_argument('--session_dir', type=str,
        default=os.path.join(BASE_PATH, 'static', 'saved_sessions'))
    parser.add_argument('--empty_session_file', type=str,
        default=os.path.join(BASE_PATH, 'static', 'saved_sessions', 'empty_session.slsess'))
    args = parser.parse_args()
    main(args)
