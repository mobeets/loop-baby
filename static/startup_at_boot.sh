#!/bin/bash

sleep 10
/home/pi/loop-baby/startup.sh
/usr/bin/python3 -u /home/pi/loop-baby/loop-baby/looper.py
