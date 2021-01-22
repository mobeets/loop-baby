#!/bin/bash

# sudo apt-get update
# sudo apt-get upgrade # nb this takes a long time

# install sooperlooper and pip3
sudo apt-get install sooperlooper python3-pip
# sudo pip3 install --upgrade setuptools

# to get numpy and pygame working
sudo apt-get install libatlas-base-dev # to get numpy working
sudo apt-get install git curl libsdl2-mixer-2.0-0 libsdl2-image-2.0-0 libsdl2-2.0-0 # to get pygame 

# stop/disable unnecessary processes to save cpu
# nb add 'dtoverlay=disable-bt' to /config/boot.txt to disable bluetooth entirely
sudo systemctl stop pisound-ctl
sudo systemctl stop pisound-btn
sudo systemctl stop bluealsa
sudo systemctl stop bluetooth
sudo systemctl stop hciuart
# nb 'mask' is patchbox-specific; acts like 'disable'
sudo systemctl mask pisound-ctl
sudo systemctl mask pisound-btn
sudo systemctl mask bluealsa
sudo systemctl mask bluetooth
sudo systemctl mask hciuart

# if having routing issues, try uncommenting the following line:
# sudo apt-get purge pulseaudio

# install required python modules
sudo pip3 install numpy pygame osc4py3

# note: if using a neotrellis, this script assumes you have already enabled I2C and SPI
# see: https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi
sudo pip3 install adafruit-circuitpython-neotrellis

echo "Done! Thank you!"
