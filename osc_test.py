import time
from osc4py3.as_eventloop import *
from osc4py3 import oscbuildparse
from osc4py3 import oscmethod as osm

OSC_CLIENT_NAME = 'sooperlooper_client'
OSC_SERVER_NAME = 'sooperlooper_server'
OSC_URL = "localhost:11016"
OSC_PORT = 9951

def handler_function(s, x, y):
    # Will receive message data unpacked in s, x, y
    print(s, x, y)

# Start the system; make client channels to send packets.
osc_startup()

try:
	osc_udp_server(OSC_URL, OSC_PORT, OSC_SERVER_NAME)
	osc_udp_client(OSC_URL, OSC_PORT, OSC_CLIENT_NAME)
	osc_method("/sl/*", handler_function)
	while True:
		msg = oscbuildparse.OSCMessage("/sl/-1", None, ["record"])
		osc_send(msg, OSC_CLIENT_NAME)
	    osc_process()
	    time.sleep(2)
except KeyboardInterrupt:
	# Properly close the system.
	osc_terminate()

"""
OSC is definitely the way to go. SL can send me updates about button press status, which will let me light/unlight buttons as pressed but only when I know they've caused the correct behavior (e.g., overdubbing)

https://osc4py3.readthedocs.io/en/latest/userdoc.html#receiving-osc-messages
http://essej.net/sooperlooper/doc_osc.html
"""