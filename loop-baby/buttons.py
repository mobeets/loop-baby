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

class Button:
    def __init__(self, name, button_number, trellis):
        self.name = name
        self.button_number
        self.trellis = trellis
        self.button_type = 'track' if type(name) is int else 'mode'

    def set_color(self, color):
        self.trellis.pixels[self.button_number] = color
        # self.trellis = trellis
        # self.button_index_map
        # self.action_button_map
        # self.mode_color_map

        # button_name -> button_number
        # 
