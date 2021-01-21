#!/bin/bash

# start sooperlooper (SL)
killall -9 sooperlooper || echo "sooperlooper was not running."
sooperlooper -p 9951 -l 1 -c 2 -t 20 &

# wait for SL to start
sleep 1

# confirm port names
jack_lsp -c

# connect input/output to route through SL
jack_connect system:capture_1 sooperlooper:common_in_1 || echo "error connecting audio (1)"
jack_connect sooperlooper:common_out_1 system:playback_1 || echo "error connecting audio (2)"
jack_connect sooperlooper:common_out_2 system:playback_2 || echo "error connecting audio (3)"

# connect USB Midi to Sooperlooper, if it is found
midi_in=`aconnect -i | grep -m1 'USB Midi' | awk '{print $2}'`
midi_out=`aconnect -o | grep -m1 'sooperlooper' | awk '{print $2}'`
echo $midi_in
echo $midi_out
if [ -z "$midi_in" ]
then
      echo "No Midi found"
else
      echo "Connecting USB Midi to Sooperlooper"
      aconnect $midi_in:0 $midi_out:0
fi

python3 ~/loop-baby/loop-baby/looper.py -v &
