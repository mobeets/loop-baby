# end previous processes
killall jackd || echo "jackd was not running."
killall sooperlooper || echo "sooperlooper was not running."

# start jack server
/usr/bin/jackd -dalsa -r48000 -p1024 -n2 -dhw:1 -s &

# wait for jack to start
sleep 5 # seconds

# start sooperlooper
sooperlooper -p 9951 -l 1 -c 2 -t 40 &

# wait for sooperlooper to start
sleep 1

# confirm port names
jack_lsp -c

jack_connect system:capture_1 sooperlooper:common_in_1 || echo "error connecting audio (1)"
jack_connect sooperlooper:common_out_1 system:playback_1 || echo "error connecting audio (2)"
jack_connect sooperlooper:common_out_2 system:playback_2 || echo "error connecting audio (3)"

