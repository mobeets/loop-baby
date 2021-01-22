import os
import sys
import time
import argparse
import subprocess

# interface options: trellis, keyboard
try:
    from trellis import Trellis
except:
    print("WARNING: Could not import Trellis. Try running 'sudo pip3 install adafruit-circuitpython-neotrellis'")
from keyboard import Keyboard

from actions import make_actions
from osc import OscSooperLooper, slider_ratio_to_gain_ratio
from save_and_recall import SLSessionManager
from button_settings import COLOR_MAP, BUTTON_MAP, SETTINGS_MAP, SCREENSAVER_TIME_SECS

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

BUTTON_PRESSED = 3
BUTTON_RELEASED = 2

class Looper:
    def __init__(self, sl_client, interface, button_map=BUTTON_MAP,
        settings_map=SETTINGS_MAP,
        screensaver_time_secs=SCREENSAVER_TIME_SECS, 
        session_dir=None, startup_color='random', verbose=False, nloops=4):

        self.verbose = verbose
        self.sl_client = sl_client
        self.sl_client.verbose = self.verbose
        self.interface = interface
        self.interface.set_callback(self.button_handler)

        actions = make_actions(self.sl_client, self.interface, button_map, settings_map)
        self.button_map = button_map
        self.loops = actions['loops']
        self.mode_buttons = actions['modes']
        self.settings = actions['settings']
        self.session_manager = SLSessionManager(actions['sessions'],
            session_dir, self.sl_client)

        self.event_id = 0 # for counting button events
        self.buttons_pressed = set()
        self.initial_nloops = nloops
        self.screensaver_time_secs = screensaver_time_secs

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
        if self.mode == 'lightshow':
            self.init_looper()
            return
        self.time_last_pressed = time.time()
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
        else:
            print('Error (unknown event.edge): {}'.format(event.edge))
            return
        if self.verbose:
            print('Button {}: ({}, {})'.format(event_type, event.number, button_name))
        self.process_button(button_name, event.number, event_type, self.event_id)

    def process_button(self, button_name, button_number, press_type, event_id):
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
                self.process_track_change(button_name, button_number, event_id)
                if self.verbose:
                    print('   ({}) track = {}'.format(self.mode, button_name))
            else:
                self.process_mode_change(button_name)
                if self.verbose:
                    print('   Mode change -> {} ({})'.format(self.mode, 'playing' if self.is_playing else 'paused'))
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
            button_numbers_set = []
            # set color of the settings buttons
            for button in self.settings:
                button.set_color()
                button_numbers_set.append(button.button_number)
            # now turn all other track buttons off
            for loop in self.loops:
                if loop.button_number not in button_numbers_set:
                    loop.set_color('off')
        elif self.mode == 'volume':
            if self.selected_track is None:
                # show tracks you can select to then set volume
                for loop in self.loops:
                    if not loop.is_enabled:
                        color = 'off'
                    elif loop.has_had_something_recorded:
                        color = 'track_recorded'
                    else:
                        color = 'track_exists'
                    loop.set_color(color)
            else:
                # visualize volume by highlighting
                # all tracks up to that proportion
                # e.g., if slider_ratio is 0.5, color the first 4 tracks
                track_count = int((len(self.loops)-1)*self.selected_track.volume_ratio)
                for loop in self.loops:
                    if loop.track <= track_count:
                        color = 'volume'
                    else:
                        color = 'off'
                    loop.set_color(color)
        elif self.mode == 'gain':
            # visualize gain level by highlighting
            # all tracks up to that proportion
            # e.g., if slider_ratio is 0.5, color the first 4 tracks
            track_count = int((len(self.loops)-1)*self.gain_slider)
            for loop in self.loops:
                if loop.track <= track_count:
                    color = 'gain'
                else:
                    color = 'off'
                loop.set_color(color)
        elif self.mode == 'monitor':
            # visualize monitor level by highlighting
            # all tracks up to that proportion
            # e.g., if slider_ratio is 0.5, color the first 4 tracks
            track_count = int((len(self.loops)-1)*self.monitor_slider)
            for loop in self.loops:
                if loop.track <= track_count:
                    color = 'monitor'
                else:
                    color = 'off'
                loop.set_color(color)

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
        elif mode == 'mute/clear':
            mode = 'clear' if previous_mode == 'mute' else 'mute'
        elif mode == 'volume/gain/monitor':
            if previous_mode == 'volume':
                if self.selected_track is None:
                    mode = 'gain'
                else:
                    # here, we have just set the volume for a track,
                    # so now we just go back to the main menu for volume
                    mode = 'volume'
            elif previous_mode == 'gain':
                mode = 'monitor'
            else:
                mode = 'volume'                

        # handle illegal actions
        if mode in ['record', 'overdub', 'mute'] and not self.is_playing:
            print('   Cannot {} when paused; otherwise loops will get out of sync!'.format(mode))
            return
        
        self.mode = mode
        if mode in ['save', 'recall'] and self.is_playing:
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
        elif mode == 'volume':
            self.selected_track = None

    def set_level(self, name, slider_ratio):
        gain_ratio = slider_ratio_to_gain_ratio(slider_ratio)
        self.sl_client.set(name, gain_ratio)

    def process_track_change(self, track, button_number, event_id):
        """
        actions depend on what mode we're in
        we also set button color based on the mode
        """
        if track < len(self.loops):
            self.loops[track-1].press()

        if self.mode == None:
            if not self.loops[track-1].is_enabled and (track-2 < 0 or self.loops[track-2].is_enabled):
                print('   Creating new loop: {}'.format(self.nloops+1))
                self.add_loop()
                # must toggle again, since before it wouldn't have applied
                self.loops[track-1].press()

        if self.mode in ['save', 'recall']:
            session = self.session_manager.sessions[track-1]
            loop = None
            setting = None
        elif self.mode == 'settings':
            loop = None
            session = None
            try:
                setting = next(s for s in self.settings if s.button_number == button_number)
            except StopIteration:
                if self.verbose:
                    print('   No setting associated with that track button.')
                return
        else:
            loop = self.loops[track-1]
            if not self.loops[track-1].is_enabled:
                loop = None
            session = None
            setting = None

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
            if setting.name == 'shutdown':
                self.shutdown_pi()
            elif setting.name == 'hard_restart':
                self.restart_pi()
            elif setting.name == 'soft_restart':
                self.restart_jack_and_sl()
            else:
                setting.press(self.loops)

        elif self.mode == 'volume':
            if self.selected_track is None:
                # here, pressing a track button selects the track
                self.selected_track = loop
            else:
                # a track has already been selected,
                # so here we set the volume of that selected track
                slider_ratio = (track-1)*1.0/(len(self.loops)-1)
                self.selected_track.set_volume(slider_ratio)

        elif self.mode == 'gain':
            self.gain_slider = (track-1)*1.0/(len(self.loops)-1)
            self.set_level('input_gain', self.gain_slider)

        elif self.mode == 'monitor':
            self.monitor_slider = (track-1)*1.0/(len(self.loops)-1)
            self.set_level('dry', self.monitor_slider)

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
            if i < len(has_audio) and has_audio[i]:
                loop.has_had_something_recorded = True

    def initialize_settings(self):
        """
        set default settings with SL
        """
        # note: these defaults override what is in the empty_session_file
        self.gain_slider = 1.0
        self.set_level('input_gain', self.gain_slider)
        # this specifies whether you can hear audio thru without recording:
        self.monitor_slider = 1.0
        self.set_level('dry', self.monitor_slider)
        for button in self.settings:
            button.init(self.loops)

    def lightshow(self):
        if self.verbose:
            print('Entering lightshow...')
        try:
            self.mode = 'lightshow'
            self.interface.lightshow()
            self.init_looper()
        except KeyboardInterrupt:
            # Properly close the system.
            self.terminate()

    def shutdown_pi(self):
        print('Shutting down!')
        self.terminate()
        subprocess.Popen(['sudo', 'halt'])

    def restart_pi(self):
        print('Rebooting!')
        self.terminate()
        subprocess.Popen(['sudo', 'reboot'])

    def restart_jack_and_sl(self, nseconds_restart_delay=7):
        print('Restarting jack and SL!')
        subprocess.Popen(['bash', os.path.join(BASE_PATH, 'startup.sh')])
        for j in range(nseconds_restart_delay):
            if j % 2 == 0:
                color = 'red'
            else:
                color = 'off'
            self.interface.set_color_all_buttons(color)
            time.sleep(1)
        # wait a generous amount of time for startup.sh to finish
        # clear loops and start from scratch
        self.init_looper()
        
    def init_looper(self):
        # load empty session and set up loops
        self.init_loops()
        self.mode = None
        self.is_playing = True

        # set input/monitor gain level, and other defaults
        self.initialize_settings()

        # handle button colors
        self.buttons_pressed = set()
        self.interface.set_color_all_buttons('off')
        self.set_mode_colors_given_mode()
        self.time_last_pressed = time.time()
        if self.verbose:
            print('Looper on!')

    def start(self):
        self.init_looper()
        try:
            while True:
                self.interface.sync()
                time.sleep(.02)
                if int(time.time() - self.time_last_pressed) > self.screensaver_time_secs:
                    # turn on screensaver lightshow
                    print((time.time(), self.time_last_pressed, time.time()-self.time_last_pressed, self.screensaver_time_secs))
                    self.lightshow()
        except KeyboardInterrupt:
            # Properly close the system.
            self.terminate()

    def terminate(self):
        if self.verbose:
            print()
            print('Ending looper...')
        self.pause()
        self.sl_client.terminate()
        self.interface.terminate()
        if self.verbose:
            print('See ya!')

def main(args):
    # start jackd and sooperlooper, and wait until finished
    if args.startup:
        startup = subprocess.Popen(['bash', args.startup_script])
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
    parser.add_argument('--startup_script',
        dest='startup_script',
        default=os.path.join(BASE_PATH, 'startup.sh'))
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
