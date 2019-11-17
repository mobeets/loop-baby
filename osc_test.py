import sys
import time
from osc_interface import OscSooperLooper

def main(OSC_CLIENT_URL):
    print("WARNING: If on pi, will need to change OSC_CLIENT_URL")
    print("OSC_CLIENT_URL: " + OSC_CLIENT_URL)

    odd = 0
    ns = 2
    try:
        osc = OscSooperLooper()
        osc.ping()
        
        # osc.set('selected_loop_num', 0)
        while True:
            # osc.hit('record')
            if odd == 0:
                print('Getting state...')
                osc.get('state', 0)
                odd = (odd + 1) % ns
            elif odd == 1:
                print('Hitting "pause".')
                osc.hit('pause', 0)
                odd = (odd + 1) % ns
            elif odd == 2:
                print('Getting state...')
                osc.get('state', 0)
                odd = (odd + 1) % ns
            elif odd == 3:
                print('Hitting "record"...')
                osc.hit('record')
                odd = (odd + 1) % ns
            # osc.get('selected_loop_num')
            # osc.get('sync_source')
            time.sleep(1)

    except KeyboardInterrupt:
        # Properly close the system.
        osc.terminate()

if __name__ == '__main__':
    OSC_CLIENT_URL = sys.argv[1]
    main(OSC_CLIENT_URL)
