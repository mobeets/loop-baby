import os
import sys
import time
import argparse
import subprocess
try:
    from trellis import Trellis
except:
    print('WARNING: Could not import Trellis')

from actions import make_actions
from osc import OscSooperLooper
from keyboard import Keyboard
from save_and_recall import SLSessionManager
from button_settings import BUTTON_MAP, COLOR_MAP, META_COMMANDS

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

BUTTON_PRESSED = 3
BUTTON_RELEASED = 2

class Looper:
    def __init__(self, sl_client, interface, button_map, meta_commands,
        session_dir=None, startup_color='random', verbose=False, nloops=4):

        self.verbose = verbose
        self.sl_client = sl_client
        self.sl_client.verbose = self.verbose
        self.interface = interface
        self.interface.set_callback(self.button_handler)

        actions = make_actions(button_map, meta_commands,
            self.sl_client, self.interface)
        self.button_map = button_map
        self.loops = actions['loops']
        self.mode_buttons = actions['modes']
        self.multipress = actions['multipress']
        self.session_manager = SLSessionManager(actions['sessions'],
            session_dir, self.sl_client)

        self.event_id = 0 # for counting button events
        self.buttons_pressed = set()
        self.initial_nloops = nloops

    def init_loops(self):
        """
        enable internal loops, and create them in SL
        """
        self.sl_client.load_empty_session()
        time.sleep(0.2) # delay to wait for SL

        self.nloops = self.initial_nloops
        # first disable loops (in case we are restarting)
        for loop in self.loops:
            loop.disable()
        # now enable up to self.nloops
        for loop in self.loops[:self.nloops]:
            loop.enable()
        # one loop exists; must tell SL about the remaining ones
        for i in range(self.nloops-1):
            self.sl_client.add_loop()

    def add_loop(self, internal_add_only=False):
        """
        add an additional loop internally, and with SL
        """
        if not internal_add_only:
            self.sl_client.add_loop()
        self.loops[self.nloops].enable()
        self.nloops += 1

    def button_handler(self, event):
        """
        this gets called when a Trellis button is pressed
        """
        self.event_id += 1
        button_name = self.button_map[event.number]

        if event.edge == BUTTON_PRESSED:
            event_type = 'pressed'
            self.buttons_pressed.add(event.number)
        elif event.edge == BUTTON_RELEASED:
            event_type = 'released'
            if event.number in self.buttons_pressed:
                self.buttons_pressed.remove(event.number)
            else:
                # false event (happens sometimes for some reason)
                return
        if self.verbose:
            print('Button {}: ({}, {})'.format(event_type, event.number, button_name))
        # check if the set of buttons currently pressed are a command
        self.buttons_pressed, found_match = self.multipress.check_for_matches(self.buttons_pressed, self)
        if found_match:
            return
        # process individual button press
        self.process_button(button_name, event_type, self.event_id)

    def process_button(self, button_name, press_type, event_id):
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
            if type(button_name) is int:
                self.process_track_change(button_name, event_id)
            else:
                self.process_mode_change(button_name)
                self.set_mode_colors_given_mode()
            self.set_track_colors_given_mode()

        # mark when a track button is unpressed
        elif press_type == 'released':
            if type(button_name) is int:
                self.loops[button_name-1].unpress()
                self.set_track_colors_given_mode()

    def set_mode_colors_given_mode(self):
        """
        set colors of all mode buttons based on self.mode
        """
        for mode_button in self.mode_buttons:
            if mode_button.name == 'play/pause':
                if self.is_playing:
                    color = 'play'
                else:
                    color = 'pause'
            elif self.mode in mode_button.name.split('/'):
                # e.g., mode_button might be 'record/overdub'
                color = self.mode
            else:
                color = 'off'
            mode_button.set_color(color)

    def set_track_colors_given_mode(self):
        """
        set colors of all track buttons based on self.mode
        """
        if self.mode == None:
            for loop in self.loops:                
                if not loop.is_enabled:
                    color = 'off'
                elif loop.is_pressed:
                    color = 'track'
                else:
                    color = 'off'
                loop.set_color(color)
        elif self.mode == 'oneshot':
            for loop in self.loops:
                if not loop.is_enabled:
                    color = 'off'
                elif loop.is_pressed:
                    color = self.mode
                elif loop.has_had_something_recorded:
                    color = 'track_recorded'
                else:
                    color = 'off'
                loop.set_color(color)
        elif self.mode in ['record', 'overdub']:
            # color buttons if track exists but isn't currently being recorded to
            for loop in self.loops:
                if not loop.is_enabled:
                    color = 'off'
                elif loop.is_recording or loop.is_overdubbing:
                    color = self.mode
                elif loop.has_had_something_recorded:
                    color = 'track_recorded'
                else:
                    color = 'track_exists'
                loop.set_color(color)
        elif self.mode == 'mute':
            for loop in self.loops:
                if not loop.is_enabled:
                    color = 'off'
                elif not loop.has_had_something_recorded:
                    color = 'track_exists'
                elif loop.is_muted:
                    color = 'mute_on'
                else:
                    color = 'mute_off'
                loop.set_color(color)
        elif self.mode in ['undo', 'redo']:
            for loop in self.loops:
                if not loop.is_enabled:
                    color = 'off'
                elif loop.is_pressed:
                    color = self.mode
                elif loop.has_had_something_recorded:
                    color = 'track_exists'
                else:
                    color = 'off'
                loop.set_color(color)
        elif self.mode == 'clear':
            for loop in self.loops:                
                if not loop.is_enabled:
                    color = 'off'
                elif loop.pressed_once:
                    if self.verbose:
                        print('    Refreshing {}'.format(loop.button_number))
                    color = 'track_pressed_once'
                elif loop.has_had_something_recorded:
                    color = 'track_exists'
                else:
                    color = 'off'
                loop.set_color(color)
        elif self.mode in ['save', 'recall']:
            for session in self.session_manager.sessions:
                if self.session_manager.exists(session.name):
                    if session.pressed_once:
                        color = 'track_pressed_once'
                    else:
                        color = 'session_exists'
                else:
                    color = 'session_empty'
                session.set_color(color)
        elif self.mode == 'settings':
            for loop in self.loops:
                loop.set_color('off')

    def pause(self):
        """
        pause all loops, and mark sync position for when we play
        """
        self.sl_client.hit('set_sync_pos', -1)
        self.sl_client.hit('pause_on', -1)
        if self.mode in ['record', 'overdub', 'mute']:
            print('   Cannot {} when paused, so setting mode -> None'.format(self.mode))
            self.mode = None
        self.is_playing = False

    def play(self):
        """
        play all loops
        then re-mute any as necessary, since 'trigger' unmutes all
        """
        if self.mode in ['save', 'recall', 'settings']:
            print('   Cannot {} when playing, so setting mode -> None'.format(self.mode))
            self.mode = None
        # when unpausing, 'trigger' restarts from where we paused
        self.sl_client.hit('trigger', -1)
        # but we must now check which tracks were muted and re-mute
        for loop in self.loops:
            loop.remute_if_necessary()
        self.is_playing = True

    def process_mode_change(self, mode):
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
        
        self.mode = mode
        if mode in ['save', 'recall', 'settings'] and self.is_playing:
            if self.verbose:
                print('   Pausing so we can switch modes to {}'.format(mode))
                self.pause()

        if mode == 'clear':
            for loop in self.loops:
                loop.pressed_once = False
        elif mode in ['save', 'recall']:
            for session in self.session_manager.sessions:
                session.pressed_once = False
            self.session_manager.sync()
        elif mode == 'settings':
            print('   Settings mode not implemented yet.')

    def process_track_change(self, track, event_id):
        """
        actions depend on what mode we're in
        we also set button color based on the mode
        """
        if self.verbose:
            print('   ({}) track = {}'.format(self.mode, track))
        if track < len(self.loops):
            self.loops[track-1].press()

        if self.mode == None:
            if not self.loops[track-1].is_enabled and (track-2 < 0 or self.loops[track-2].is_enabled):
                print('   Creating new loop: {}'.format(self.nloops+1))
                self.add_loop()
                # must toggle again, since before it wouldn't have applied
                self.loops[track-1].press()

        if self.mode not in ['save', 'recall', 'settings']:
            loop = self.loops[track-1]
            if not self.loops[track-1].is_enabled:
                loop = None
            session = None
        else:
            session = self.session_manager.sessions[track-1]
            loop = None

        if self.mode == 'oneshot':
            # warning: once you hit this once, this loop will forever
            # be out of sync; this is because we cannot store the sync_pos
            # and then restore it later
            if loop is not None:
                loop.oneshot()

        elif self.mode in ['record', 'overdub']:
            if loop is not None:
                loop.toggle(self.mode, event_id)
            else:
                print('   Loop index does not exist for '.format(self.mode))

        elif self.mode == 'mute':
            if loop is not None:
                loop.toggle(self.mode)
            else:
                print('   Loop index does not exist for {}'.format(self.mode))

        elif self.mode == 'undo':
            if loop is not None:
                loop.undo()
            else:
                print('   Loop index does not exist for {}'.format(self.mode))

        elif self.mode == 'redo':
            if loop is not None:
                loop.redo()
            else:
                print('   Loop index does not exist for {}'.format(self.mode))

        elif self.mode == 'clear':
            if loop is not None:
                if loop.pressed_once:
                    if self.verbose:
                        print('   Clearing track {}'.format(track))
                    loop.pressed_once = False
                    loop.clear()
                else:
                    if self.verbose:
                        print('   Pressed track {} once for {}'.format(track, self.mode))
                    loop.pressed_once = True
            else:
                print('   Loop index does not exist for {}'.format(self.mode))

        elif self.mode == 'save':
            if not self.session_manager.exists(session.name) or session.pressed_once:
                self.session_manager.save_session(session.name, self.loops)
                session.pressed_once = False
                if self.verbose:
                    print('   Saving session at index {}'.format(track-1))
            else:
                if self.verbose:
                    print('   Pressed track {} once for {}'.format(track, self.mode))
                session.pressed_once = True

        elif self.mode == 'recall':
            if self.session_manager.exists(session.name) and session.pressed_once:
                self.recall_session(session)
                session.pressed_once = False
                if self.verbose:
                    print('   Loading session at index {}'.format(track-1))
            elif not session.pressed_once:
                if self.verbose:
                    print('   Pressed track {} once for {}'.format(track, self.mode))
                session.pressed_once = True
            else:
                print('   Saved session does not exist at track {}'.format(track))

        elif self.mode == 'settings':
            print('   Settings track not implemented yet.')

    def recall_session(self, session):
        """
        when recalling a session, we have to make sure
        we have the right number of loops
        """
        has_audio = self.session_manager.load_session(session.name)
        nloops = len(has_audio)
        # remove extra loops (internally)
        for loop in self.loops[nloops:]:
            loop.disable()
        self.nloops = nloops
        # mark any existing loops that have something recorded
        for i,loop in enumerate(self.loops):
            loop.has_had_something_recorded = has_audio[i]

    def init_looper(self):
        # load empty session
        self.init_loops()
        self.mode = None
        self.is_playing = True
        self.buttons_pressed = set()
        self.interface.set_color_all_buttons('off')
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
        self.sl_client.terminate()
        self.interface.terminate()
        if self.verbose:
            print('See ya!')

def main(args):
    # start jackd and sooperlooper, and wait until finished
    if args.startup:
        startup = subprocess.Popen(['bash', os.path.join(BASE_PATH, 'startup.sh')])
        startup.communicate()

    # connect to SooperLooper via OSC
    if args.verbose:
        print('Setting up Sooper Looper OSC client...')
    sl_client = OscSooperLooper(client_url=args.osc_url,
        empty_session=args.empty_session_file)

    # connect with either trellis PCB or keyboard
    if args.verbose:
        print('Initializing {} interface...'.format(args.interface))
    if args.interface == 'trellis':
        interface = Trellis(startup_color=args.color)
    elif args.interface == 'keyboard':
        interface = Keyboard(BUTTON_PRESSED, BUTTON_RELEASED)
    interface.set_color_map(COLOR_MAP)
    
    looper = Looper(sl_client=sl_client,
        interface=interface,
        button_map=BUTTON_MAP,
        meta_commands=META_COMMANDS,
        session_dir=args.session_dir,
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
        dest='verbose', action='store_true')
    parser.add_argument('-s', '--startup',
        dest='startup', action='store_true')
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
