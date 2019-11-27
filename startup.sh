
# start jack server
/usr/bin/jackd -dalsa -r48000 -p1024 -n2 -dhw:1 -s > jackd_errors.log 2>&1 &

# wait for jack to start
sleep 5 # seconds

# start sooperlooper
sooperlooper -p 9951 -l 4 -c 2 -t 40 &

# wait for sooperlooper to start
sleep 1

# confirm port names
jack_lsp -c

jack_connect system:capture_1 sooperlooper:common_in_1
jack_connect sooperlooper:common_out_1 system:playback_1
jack_connect sooperlooper:common_out_2 system:playback_2
