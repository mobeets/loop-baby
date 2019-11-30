
BUTTON_MAP = { # arranged as installed
	12: 1,  8: 2,  4: 3,  0: 4,
	13: 5,  9: 6,  5: 7,  1: 8,
	14: 'oneshot', 10: 'save/recall', 6: 'settings', 2: 'clear',
	15: 'play/pause', 11: 'record/overdub', 7: 'undo/redo', 'mute': 3
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
    }

META_COMMANDS = {
    'shutdown': { # shutdown the pi,
            'command': [13, 9, 5, 1],
            'restart_looper': False,
            'callback': lambda: os.system('sudo halt')
        },
    'hard_restart': { # restart the pi,
            'command': [14, 10, 6, 2],
            'restart_looper': False,
            'callback': lambda: os.system('sudo reboot')
        },
    'soft_restart': { # calls ./startup.sh
            'command': [15, 11, 7, 3],
            'restart_looper': True,
            'callback': lambda: os.system('.' + os.path.join(BASE_PATH, 'startup.sh'))
        },
}
