# loop-baby
portable audio looper using raspberry pi, sooperlooper, and a [neotrellis](https://www.adafruit.com/product/3954) pcb

## requirements

hardware:

- raspberry pi (3B) with USB audio interface
- [neotrellis pcb](https://www.adafruit.com/product/3954) and [silicone buttons](https://www.adafruit.com/product/1611) for controlling the looper
- laser-cut enclosure (`static/design.ai`)
- full [parts list](https://github.com/mobeets/loop-baby/wiki/Parts-list) with costs

software:

- python 3 with various packages (listed in `requirements.txt`)
- [jackd](https://jackaudio.org/): for routing audio
- [sooperlooper](http://essej.net/sooperlooper/): for looping

## running

current start-up process (these lines can be added to `/etc/rc.local` to be run on boot):

```
./startup.sh
python3 looper.py -v
```

