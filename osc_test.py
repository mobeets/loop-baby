"""
1. Start sooperlooper
    - /Applications/SooperLooper.app/Contents/MacOS/slgui -H localhost -P 9951
    - /Applications/SooperLooper.app/Contents/MacOS/sooperlooper -p 9951 -l 1 -c 2 -t 40 -m /Users/mobeets/.sooperlooper/default_midi.slb -D no
    - I used the gui above so I could ensure I was sending record messages, but the sooperlooper command worked as well
2. Run this script
    - Should send record commands, and receive ping response

Reference:
- https://github.com/aquamatt/loopercontrol
"""

import time
from osc4py3.as_eventloop import *
from osc4py3 import oscbuildparse
from osc4py3 import oscmethod as osm

OSC_CLIENT_NAME = 'sooperlooper_client'
OSC_CLIENT_URL = "thisbemymachine.verizon.net"
OSC_CLIENT_PORT = 9951
OSC_SERVER_URL = "0.0.0.0"
OSC_SERVER_PORT = 7777
OSC_SERVER_NAME = 'sooperlooper_server'

MAX_LOOP_COUNT = 8
MINIMUM_LOOP_DURATION = 60 # seconds
MONO, STEREO = (1, 2)

class OscBase:
    def __init__(self, client_url=OSC_CLIENT_URL, client_port=OSC_CLIENT_PORT, client_name=OSC_CLIENT_NAME, server_url=OSC_SERVER_URL, server_port=OSC_SERVER_PORT, server_name=OSC_SERVER_NAME):

        self.client_url = client_url
        self.client_port = client_port
        self.client_name = client_name
        self.server_url = server_url
        self.server_port = server_port
        self.server_name = server_name

        osc_startup()
        self.make_client()
        self.make_server()

    def make_client(self):
        # sends messages to sooperlooper
        osc_udp_client(self.client_url, self.client_port, self.client_name)

    def make_server(self):
        self.return_url = "osc.udp://{}:{}".format(self.server_url, self.server_port)

        # receives messages from self or sooperlooper
        osc_udp_server(self.server_url, self.server_port, self.server_name)

    def terminate(self):
        osc_terminate()

    def _send_message(self, msg):
        osc_send(msg, self.client_name)
        osc_process()

    def flex_handler(self, address, *args):
        """
        use this for variable # of arguments in osc message's data.
        need to speciy argscheme OSCARG_DATA in osc_method() call
        """
        print('received msg to: {}; msg = {}'.format(address, *args))

class OscSooperLooperInterface(OscBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        osc_method("/ping", self.flex_handler, argscheme=osm.OSCARG_ADDRESS + osm.OSCARG_DATA)
        osc_method("/get", self.flex_handler, argscheme=osm.OSCARG_ADDRESS + osm.OSCARG_DATA)

        self.actions = ["record", "overdub", "multiply", "insert", "replace", "reverse", "mute", "undo", "redo", "oneshot", "trigger", "substitute", "undo_all", "redo_all", "mute_on", "mute_off", "solo", "pause", "solo_next", "solo_prev", "record_solo", "record_solo_next", "record_solo_prev", "set_sync_pos", "reset_sync_pos"]
        self.params = {'unknown': -1, 'off': 0, 'waitstart': 1, 'recording': 2,
            'waitstop': 3, 'playing': 4, 'overdubbing': 5, 'multiplying': 6,
            'inserting': 7, 'replacing': 8, 'delay': 9, 'muted': 10,
            'scratching': 11, 'oneshot': 12, 'substitute': 13, 'paused': 14,
            'sync_source': None, 'selected_loop_num': None}
        
    def hit(self, action, loop=-3):
        """
        loop == -3: selected loop
        loop == -1: all loops
        otherwise: loop with that index

        source: http://essej.net/sooperlooper/doc_osc.html
        """
        assert action in self.actions
        assert loop >= -3 and loop <= MAX_LOOP_COUNT-1

        msg = oscbuildparse.OSCMessage("/sl/{}/hit".format(loop),
            None, [action])
        self._send_message(msg)

    def get(self, param, loop=None):
        """
        """
        assert param in self.params.keys()
        if loop is None:
            msg = oscbuildparse.OSCMessage("/get",
                None, [param, self.return_url, "/get"])
        else:
            assert loop >= -3 and loop <= MAX_LOOP_COUNT-1
            msg = oscbuildparse.OSCMessage("/sl/{}/get".format(loop),
                None, [param, self.return_url, "/get"])
        self._send_message(msg)

    def set(self, param, value, loop=None):
        """
        sync_source: [-3 = internal, -2 = midi, -1 = jack, 0 = none, # > 0 = loop number (1 indexed)]
        """
        assert param in self.params.keys()
        if param == 'sync_source':
            assert value >= -3 and value <= MAX_LOOP_COUNT
        if param == 'selected_loop_num':
            assert value >= 0 and value <= MAX_LOOP_COUNT-1
        if loop is None:
            msg = oscbuildparse.OSCMessage("/set", None, [param, value])
        else:
            assert loop >= -3 and loop <= MAX_LOOP_COUNT-1
            msg = oscbuildparse.OSCMessage("/sl/{}/set".format(loop),
                None, [param, value])
        self._send_message(msg)

    def add_loop(self):
        """
        /loop_add  i:#channels  f:min_length_seconds
        """
        msg = oscbuildparse.OSCMessage("/loop_add", None,
            [STEREO, MINIMUM_LOOP_DURATION])
        self._send_message(msg)

    def ping(self):
        msg = oscbuildparse.OSCMessage("/ping", None, [self.return_url, "/ping"])
        self._send_message(msg)

def main():
    print("WARNING: If on pi, will need to change OSC_CLIENT_URL")
    print("OSC_CLIENT_URL: " + OSC_CLIENT_URL)

    try:
        osc = OscSooperLooperInterface()

        osc.set('selected_loop_num', 0)
        while True:
            # osc.hit('record')
            # osc.ping()
            # osc.get('recording')
            # osc.get('playing', -3)
            # osc.get('playing', -1)
            osc.get('playing', 0)
            osc.get('playing')
            osc.hit('pause', 0)
            # osc.set('playing', 1)
            # osc.get('playing', 2)
            # osc.get('paused')
            # osc.get('paused', 2)
            # osc.get('sync_source')
            osc.get('selected_loop_num')
            time.sleep(2)

    except KeyboardInterrupt:
        # Properly close the system.
        osc.terminate()

if __name__ == '__main__':
    main()
