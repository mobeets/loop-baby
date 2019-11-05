"""
1. Start sooperlooper
    - /Applications/SooperLooper.app/Contents/MacOS/slgui -H localhost -P 9951
    - /Applications/SooperLooper.app/Contents/MacOS/sooperlooper -p 9951 -l 1 -c 2 -t 40 -m /Users/mobeets/.sooperlooper/default_midi.slb -D no
    - I used the gui above so I could ensure I was sending record messages, but the sooperlooper command worked as well
2. Run this script
    - Should send record commands, and receive ping response

Next steps:
1. Try out other commands and responses
    - try to keep track of recording status
"""

import time
from osc4py3.as_eventloop import *
from osc4py3 import oscbuildparse
from osc4py3 import oscmethod as osm

OSC_CLIENT_NAME = 'sooperlooper_client'
OSC_URL = "thisbemymachine.verizon.net"
OSC_PORT = 9951

OSC_SERVER_URL = "0.0.0.0"
OSC_SERVER_PORT = 7777
OSC_SERVER_NAME = 'sooperlooper_server'
OSC_RET_URL = "osc.udp://" + OSC_SERVER_URL + ":" + str(OSC_SERVER_PORT)

print("WARNING: If on pi, will need to change OSC_URL")
print("OSC_URL: " + OSC_URL)
print("OSC_RET_URL: " + OSC_RET_URL)

def flex_handler(address, *args):
    '''
    use this for variable # of arguments in osc message's data.
    need to speciy argscheme OSCARG_DATA in osc_method() call
    '''

    print('received message addressed to: {}'.format(address))
    print('message: {}'.format(*args))

# Start the system; make client channels to send packets.
osc_startup()

try:
    # sends messages to sooperlooper
    osc_udp_client(OSC_URL, OSC_PORT, OSC_CLIENT_NAME)

    # sends messages to self
    osc_udp_client(OSC_SERVER_URL, OSC_SERVER_PORT, 'test')

    # receives messages from self or sooperlooper
    osc_udp_server(OSC_SERVER_URL, OSC_SERVER_PORT, OSC_SERVER_NAME)
    osc_method("/sl", flex_handler, argscheme=osm.OSCARG_ADDRESS + osm.OSCARG_DATA)

    while True:
        msg = oscbuildparse.OSCMessage("/sl/-3/hit", ',s', ["record"])
        osc_send(msg, OSC_CLIENT_NAME)

        msg = oscbuildparse.OSCMessage("/ping", None, [OSC_RET_URL, "/sl"])
        osc_send(msg, OSC_CLIENT_NAME)

        osc_process()
        time.sleep(2)
except KeyboardInterrupt:
    # Properly close the system.
    osc_terminate()
