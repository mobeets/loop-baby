import time
import numpy as np
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

def slider_ratio_to_gain_ratio(slider_ratio):
    gr = np.power(2.0,(np.sqrt(np.sqrt(np.sqrt(slider_ratio)))*198.0-198.0)/6.0)
    return 0.0 if np.isclose(gr, 0.0) else float(gr)

def gain_ratio_to_slider_ratio(gain_ratio):
    sr = np.power((6.0*np.log(gain_ratio)/np.log(2.0)+198.0)/198.0, 8.0)
    return float(sr)

class OscBase:
    def __init__(self, client_url=OSC_CLIENT_URL, client_port=OSC_CLIENT_PORT, client_name=OSC_CLIENT_NAME, server_url=OSC_SERVER_URL, server_port=OSC_SERVER_PORT, server_name=OSC_SERVER_NAME,
        empty_session=None):

        self.client_url = client_url
        self.client_port = client_port
        self.client_name = client_name
        self.server_url = server_url
        self.server_port = server_port
        self.server_name = server_name
        self.empty_session = empty_session # .slsess

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

    def handle_osc_message(self, address, *args):
        """
        use this for variable # of arguments in osc message's data.
        need to speciy argscheme OSCARG_DATA in osc_method() call
        """
        print('received msg to: {}; msg = {}'.format(address, *args))

class OscSooperLooper(OscBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        osc_method("/ping", self.handle_osc_message,
            argscheme=osm.OSCARG_ADDRESS + osm.OSCARG_DATA)
        osc_method("/get", self.handle_get,
            argscheme=osm.OSCARG_ADDRESS + osm.OSCARG_DATA)

        self.actions = ["record", "overdub", "multiply", "insert",
            "replace", "reverse", "mute", "undo", "redo", "oneshot",
            "trigger", "substitute", "undo_all", "redo_all", "mute_on",
            "mute_off", "solo", "pause", "solo_next", "solo_prev",
            "record_solo", "record_solo_next", "record_solo_prev",
            "set_sync_pos", "reset_sync_pos", "mute_on", "mute_off",
            "pause_on", "pause_off"]
        self.state_lookup = {0: 'off', 1: 'waitstart',
            2: 'recording', 3: 'waitstop', 4: 'playing',
            5: 'overdubbing', 6: 'multiplying',
            7: 'inserting', 8: 'replacing', 9: 'delay',
            10: 'muted', 11: 'scratching', 12: 'oneshot',
            13: 'substitute', 14: 'paused', -1: 'unknown'}
        self.global_params = ['dry', 'wet', 'input_gain', 'sync_source',
            'tap_tempo', 'save_loop', 'auto_disable_latency',
            'select_next_loop', 'select_prev_loop', 'select_all_loops',
            'selected_loop_num']
        self.track_params = ['rec_thresh', 'feedback', 'dry', 'wet',
            'input_gain', 'rate', 'scratch_pos', 'delay_trigger', 'quantize',
            'round', 'redo_is_tap', 'sync', 'playback_sync', 'use_rate',
            'fade_samples', 'use_feedback_play', 'use_common_ins',
            'use_common_outs', 'relative_sync', 'use_safety_feedback',
            'pan_1', 'pan_2', 'pan_3', 'pan_4', 'input_latency',
            'output_latency', 'trigger_latency', 'autoset_latency',
            'mute_quantized']
        self.state = 'off'
        self.verbose = False

    def handle_get(self, address, *args):
        if not args or len(args[0]) != 3:
            print('Unexpected get: {}'.format(*args))
        kind = args[0][1]
        if kind == 'state':
            self.state = self.state_lookup.get(args[0][2])
            print('state: {}, value: {}'.format(self.state, args[0][2]))
        else:
            print('{}: {}'.format(kind, args[0][2]))

    def hit(self, action, loop=-3):
        """
        loop == -3: selected loop
        loop == -1: all loops
        otherwise: loop with that index

        source: http://essej.net/sooperlooper/doc_osc.html
        """
        assert action in self.actions
        assert loop >= -3 and loop <= MAX_LOOP_COUNT-1

        if self.verbose:
            print("Hit action={}, loop={}".format(action, loop))
        msg = oscbuildparse.OSCMessage("/sl/{}/hit".format(loop),
            None, [action])
        self._send_message(msg)

    def get(self, param, loop=None):
        """
        /get  s:param  s:return_url  s:retpath
        OR
        /sl/#/get  s:control  s:return_url  s: return_path
          Which returns an OSC message to the given return url and path with
          the arguments:
              i:loop_index  s:control  f:value
        """
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
        /set  s:param  f:value
        sync_source: [-3 = internal, -2 = midi, -1 = jack, 0 = none, # > 0 = loop number (1 indexed)]
        """
        if param in 'sync_source':
            assert value >= -3 and value <= MAX_LOOP_COUNT
        if param == 'selected_loop_num':
            assert value >= 0 and value <= MAX_LOOP_COUNT-1
        if loop is None:
            msg = oscbuildparse.OSCMessage("/set", None, [param, value])
        else:
            assert loop >= -3 and loop <= MAX_LOOP_COUNT-1
            msg = oscbuildparse.OSCMessage("/sl/{}/set".format(loop),
                None, [param, value])
        if self.verbose:
            print("Set param={}, value={}, loop={}".format(param, value, loop))
        self._send_message(msg)

    def load_empty_session(self):
        """
        /load_session   s:filename  s:return_url  s:error_path
        """
        if self.empty_session is None:
            print('No empty session file (.slsess) was found.')
            return
        print('Loading empty session from file: {}'.format(self.empty_session))
        msg = oscbuildparse.OSCMessage("/load_session", None,
            [self.empty_session, self.return_url, "/ping"])
        self._send_message(msg)

    def load_session(self, infile):
        """
        /load_session   s:filename  s:return_url  s:error_path
        """
        print('Loading session from file: {}'.format(infile))
        msg = oscbuildparse.OSCMessage("/load_session", None,
            [infile, self.return_url, "/ping"])
        self._send_message(msg)

    def save_session(self, outfile):
        """
        /save_session   s:filename  s:return_url  s:error_path
        saves current session description to filename.
        """
        print('Saving session to file: {}'.format(outfile))
        msg = oscbuildparse.OSCMessage("/save_session", None,
            [outfile, self.return_url, "/ping"])
        self._send_message(msg)

    def save_loop_audio(self, index, outfile):
        """
        /sl/#/save_loop   s:filename  s:format  s:endian  s:return_url  s:error_path
       saves current loop to given filename, may return error to error_path
       format and endian currently ignored, always uses 32 bit IEEE float WAV
        """
        print('Saving audio in loop {} to file: {}'.format(index, outfile))
        msg = oscbuildparse.OSCMessage("/sl/{}/save_loop".format(index),
            None, [outfile, '', '', self.return_url, "/ping"])
        self._send_message(msg)

    def add_loop(self):
        """
        /loop_add  i:#channels  f:min_length_seconds
        """
        msg = oscbuildparse.OSCMessage("/loop_add", None,
            [STEREO, MINIMUM_LOOP_DURATION])
        self._send_message(msg)

    def ping(self):
        """
        /ping s:return_url s:return_path
         If engine is there, it will respond with to the given URL and PATH
          with an OSC message with arguments:
             s:hosturl  s:version  i:loopcount
        """
        msg = oscbuildparse.OSCMessage("/ping", None, [self.return_url, "/ping"])
        self._send_message(msg)
