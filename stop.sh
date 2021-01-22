#!/bin/sh
killall sooperlooper
kill $(pgrep -f looper.py)
