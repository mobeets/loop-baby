# loop-baby
looper using raspberry pi, sooperlooper, and a [neotrellis](https://www.adafruit.com/product/3954) pcb

## installation

an incomplete list of things I did:

- Upgrade system just for fun
	- `sudo-apt get update`, `sudo apt-get upgrade`, `sudo pip3 install --upgrade setuptools`, AND `sudo pip install --upgrade setuptools`
		- the last line was required to prevent install of neotrellis library install from breaking due to pip problems
	- Warning: This will take FOREVER
- Enabled I2C and SPI, and installed CircuitPython libraries in Python3
	- [source](https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi)
	- Run blinkatest.py to confirm
- Install Neotrellis library in Python3
	- `sudo pip3 install adafruit-circuitpython-neotrellis`
- Default audio interface set-up: Create file ~/.asoundrc
	````
	pcm.!default {
	        type hw
	        card 0
	        device 0
	}
	ctl.!default {
	        type hw
	        card 0
	        device 0
	}
	````
	- where 'card 0' is replaced by the device number when running 'aplay -l'. Then confirm it's working by running 'alsamixer'
- Installed cffi and JACK-Client using pip3
- Installed fluidsynth and qsynth using apt-get
- Installed a2jmidi using apt-get (for converting alsa-midi, which sooperlooper uses, to jack-midi)
- pip3 install osc4py3

## running

Current start-up:

1. `/usr/bin/jackd -T -ndefault -R -d alsa &`
2. `qjackctl &`
3. start sooperlooper via gui
4. `python3 looper.py -v`
