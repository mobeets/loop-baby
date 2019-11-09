import random

SCL = None
SDA = None

class Bus:
    def I2C(self, *args, **kwargs):
        pass
busio = Bus()

class Event:
    def __init__(self, number, edge):
        self.number = number
        self.edge = edge

class NeoTrellis:
    EDGE_RISING = 3
    EDGE_FALLING = 2

    def __init__(self, *args, **kwargs):
        self.callbacks = [None]*16
        self.pixels = [0]*16
        self.button = None
        self.pressed = False
        self.time = 0
        self.time_delay = 10
        self.threshold = 0.01
        self.last_was_mode = False
        self.tracks = [0,1,4,5,8,9,12,13]

    def activate_key(self, *args, **kwargs):
        pass

    def sync(self):
        """
        hit a random button every so often
        """
        if self.pressed:
            # handle previously pressed button
            self.time += 1
            if self.time == self.time_delay:
                # release the button!
                event = Event(self.button, NeoTrellis.EDGE_FALLING)
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
            event = Event(self.button, NeoTrellis.EDGE_RISING)
            self.callbacks[self.button](event)
