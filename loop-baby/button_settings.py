import os
import subprocess

SCREENSAVER_TIME_SECS = 60*5

BUTTON_MAP = { # arranged as installed
	12: 1,  8: 2,  4: 3,  0: 4,
	13: 5,  9: 6,  5: 7,  1: 8,
	14: 'oneshot', 10: 'save/recall', 6: 'settings', 2: 'volume/gain',
	15: 'play/pause', 11: 'record/overdub', 7: 'undo/redo', 3: 'mute/clear'}

SETTINGS_MAP = {
	12: {'param': 'sync_source',
		'options': [('none', 0), ('track_1', 1), ('track_2', 2), ('midi', -2)]},
	8: {'param': 'quantize',
		'options': [('off', 0), ('8th', 2), ('cycle_4', 1), ('cycle_8', 1),
			('cycle_16', 1), ('loop', 3)]}
}

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
    'sync_source_none': 'off',
    'sync_source_track_1': 'red',
    'sync_source_track_2': 'orange',
    'sync_source_midi': 'yellow',
    'quantize_off': 'off',
    'quantize_8th': 'red',
    'quantize_cycle_4': 'orange',
    'quantize_cycle_8': 'yellow',
    'quantize_cycle_16': 'green',
    'quantize_loop': 'blue',
    'volume': 'red',
    'gain': 'orange',
}

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

META_COMMANDS = {
    'shutdown': { # shutdown the pi,
        'command': [12, 0, 15, 3],
        'restart_looper': False,
        'callback': lambda looper: subprocess.Popen(['sudo', 'halt'])
    },
	'hard_restart': { # restart the pi,
        'command': [13, 9, 5, 1],
        'restart_looper': False,
        'callback': lambda looper: subprocess.Popen(['sudo', 'reboot'])        
    },
	'soft_restart': { # calls ./startup.sh
        'command': [14, 10, 6, 2],
        'restart_looper': True,
        'callback': lambda looper: subprocess.Popen(['bash', os.path.join(BASE_PATH, 'startup.sh')])
        },
   # 'light_show': {
   #      'command': [15, 11, 14, 10],
   #      'restart_looper': False,
   #      'callback': lambda looper: looper.lightshow(),
   #      },
}
