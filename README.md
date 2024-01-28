# loop-baby
portable audio looper using raspberry pi, sooperlooper, and a [neotrellis](https://www.adafruit.com/product/3954) pcb

<img alt="alt_text" width="40%" src="static/photos/box.jpg" /><img alt="alt_text" width="31%" src="static/photos/guts.jpeg" /> <img alt="alt_text" width="28%" src="static/photos/design.png" />

goal: an affordable audio looper with quantization

how it works:
- audio input/output via a usb audio adapter
- midi clock signal via a midi-usb cable
- raspberry pi (with Raspbian) routes audio through [sooperlooper](http://essej.net/sooperlooper/)
- buttons interface with sooperlooper (via `looper.py`) to control recording/playback/saving/loading/etc.

## requirements

hardware:

- raspberry pi (3B) with USB audio interface
- [neotrellis pcb](https://www.adafruit.com/product/3954) and [silicone buttons](https://www.adafruit.com/product/1611) for controlling the looper
- laser-cut enclosure (`static/photos/design.ai`)
- full [parts list](https://github.com/mobeets/loop-baby/wiki/Parts-list) with costs

software:

- python 3 with various packages (listed in `requirements.txt`)
- [jackd](https://jackaudio.org/): for routing audio
- [sooperlooper](http://essej.net/sooperlooper/): for looping

## running

`python3 looper.py -v -s`

the loops will be time quantized if you provide a clock signal via a midi-usb cable

## issues

for mysterious reasons I could never quite understand, jackd or sooperlooper often silently crash. see `static/notes/issues.txt` for other odd bugs I could never fully resolve.
