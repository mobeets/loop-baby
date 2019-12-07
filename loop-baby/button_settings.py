import os
import subprocess

BUTTON_MAP = { # arranged as installed
	12: 1,  8: 2,  4: 3,  0: 4,
	13: 5,  9: 6,  5: 7,  1: 8,
	14: 'oneshot', 10: 'save/recall', 6: 'settings', 2: 'clear',
	15: 'play/pause', 11: 'record/overdub', 7: 'undo/redo', 3: 'mute'}

SETTINGS_MAP = { # button_number: (param, name, value)
	12: ('sync_source', 'track_1', 1), 8: ('sync_source', 'track_2', 2),
		4: ('sync_source', 'midi', -2), 0: ('sync_source', 'none', 0),
	13: ('quantize', 'off', 0), 9: ('quantize', 'cycle', 1),
		5: ('quantize', '8th', 2), 1: ('quantize', 'loop', 3),
}

INIT_SETTINGS = {'sync_source': 'none', 'quantize': 'off'}

COLOR_MAP = {
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
    'sync_source_track_1': 'gray',
    'sync_source_track_2': 'gray',
    'sync_source_midi': 'salmon',
    'sync_source_none': 'darkgray',
    'quantize_off': 'gray',
    'quantize_cycle': 'gray',
    'quantize_8th': 'salmon',
    'quantize_loop': 'darkgray',
    }

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

META_COMMANDS = {
    'shutdown': { # shutdown the pi,
        'command': [12, 0, 15, 3],
        'restart_looper': False,
        'callback': lambda: subprocess.Popen(['sudo', 'halt'])
    },
	'hard_restart': { # restart the pi,
        'command': [14, 10, 6, 2],
        'restart_looper': False,
        'callback': lambda: subprocess.Popen(['sudo', 'reboot'])        
    },
	'soft_restart': { # calls ./startup.sh
        'command': [15, 11, 7, 3],
        'restart_looper': True,
        'callback': lambda: subprocess.Popen(['bash', os.path.join(BASE_PATH, 'startup.sh')])
        },
}
