"""
/usr/bin/jackd -T -ndefault -R -d alsa -d hw:system -n 3 -r 44100 -p 128 &
a2midid -e &
sooperlooper -q -U osc.udp://localhost:18978/ -p 9951 -l 1 -c 2 -t 40 -m /usr/share/sooperlooper/presets/midiwizard.slb
"""
import sys
import time
import jack

def make_ports_and_connections(client, midi_out):
    """
    Need to check to make sure these connections do not already exist
    """

    # audio in
    try:
        client.connect('system:capture_1', 'sooperlooper:common_in_1')
        client.connect('system:capture_2', 'sooperlooper:common_in_2')
    except jack.JackError:
        pass

    # audio out
    try:
        client.connect('sooperlooper:common_out_1', 'system:playback_1')
        client.connect('sooperlooper:common_out_2', 'system:playback_2')
    except jack.JackError:
        pass

    # midi in    
    midi_ins = client.get_ports(is_midi=True, is_input=True)
    connect_to = [x for x in midi_ins if 'sooperlooper' in x.name]
    if not connect_to:
        print("ERROR: Could not find midi port. Connected ports:")
        print(client.get_ports())
        return False
    else:
        connect_to = connect_to[0]
    print('Connecting midi to {}'.format(connect_to))
    # client.connect(midi_out, connect_to)
    return True

if __name__ == '__main__':
    client = jack.Client('test')
    midi_out = client.midi_outports.register('output')
    try:
        with client:
            success = make_ports_and_connections(client, midi_out)
            if not success:
                sys.exit()
            print('#' * 80)
            print('press Return to quit')
            print('#' * 80)
            time.sleep(.02)
            input()
    except KeyboardInterrupt:
        # handle quitting with ctrl+c
        pass
