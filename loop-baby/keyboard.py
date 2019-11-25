import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import random
import pygame

KEYBOARD_MAP = {
    '1': 12, '2': 8,  '3': 4, '4': 0,
    'q': 13, 'w': 9,  'e': 5, 'r': 1,
    'a': 14, 's': 10, 'd': 6, 'f': 2,
    'z': 15, 'x': 11, 'c': 7, 'v': 3
    }

class Event:
    def __init__(self, number, edge):
        self.number = number
        self.edge = edge

class Keyboard:
    def __init__(self, pressed_code, released_code):
        self.pressed_code = pressed_code
        self.released_code = released_code

        self.callbacks = [None]*16
        self.pixels = [0]*16
        self.button = None
        self.pressed = False
        self.time = 0
        self.time_delay = 10
        self.threshold = 0.01
        self.last_was_mode = False
        self.tracks = [0,1,4,5,8,9,12,13]
        self.keyboard_map = dict((eval('pygame.' + 'K_' + k),v) for k,v in KEYBOARD_MAP.items())
        self.sync = self.keyboard_sync
        pygame.display.init()

    def set_callback(self, fcn):
        self.callbacks = [fcn for i in range(len(self.callbacks))]

    def activate_key(self, *args, **kwargs):
        pass

    def keyboard_sync(self):
        """
        generate button press events upon keyboard presses
        """
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                raise KeyboardInterrupt
            if not hasattr(event, 'key'):
                continue
            if event.key in self.keyboard_map:
                self.button = self.keyboard_map[event.key]
                if event.type == pygame.KEYDOWN:
                    btn_event = Event(self.button, self.pressed_code)
                    print('----------------------')
                    print('FAKE keypress {}'.format(self.button))
                    self.callbacks[self.button](btn_event)
                elif event.type == pygame.KEYUP:
                    btn_event = Event(self.button, self.released_code)
                    self.callbacks[self.button](btn_event)

    def random_sync(self):
        """
        hit a random button every so often
        """
        if self.pressed:
            # handle previously pressed button
            self.time += 1
            if self.time == self.time_delay:
                # release the button!
                event = Event(self.button, self.released_code)
                self.callbacks[self.button](event)
                self.pressed = False
                self.button = None
            return
        if random.random() < self.threshold:
            # press a random button!
            # self.button = random.randint(0,15)
            self.button = 11
            while self.last_was_mode and self.button not in self.tracks:
                # if we pressed a mode button last, press a track button next
                # self.button = random.randint(0,15)
                self.button = 12
            self.pressed = True
            self.time = 0
            self.last_was_mode = self.button not in self.tracks
            print('----------------------')
            print('FAKE press {}'.format(self.button))
            event = Event(self.button, self.pressed_code)
            self.callbacks[self.button](event)

    def define_color_group(self, group_name, button_numbers):
        pass

    def set_color_of_group(self, group_name, color):
        pass

    def set_color(self, index, color, uncolor=None):
        pass

    def un_color(self, index):
        pass

    def load_empty_session(self):
        pass

    def terminate(self):
        pass
